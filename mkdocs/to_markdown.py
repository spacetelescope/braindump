"""Script to convert Sphinx RST files to mkdocs markdown files.

Accepts one or more input files or directories and a single output directory.

# Dependencies
- pandoc binary for initial RST to markdown conversion
- click Python package for args parsing (This is already a dependency of mkdocs)

# Usage
```bash
to_markdown -m asdf old_docs/my_file.rst -o docs/  # Convert single file
to_markdown -m asdf old_docs -o docs/  # Convert entire directory
```

The `-m <module>` argument

# Extending
This script can be extended or modified by adding/removing functions in `TRANSFORMS`.
"""

import importlib
import re
import subprocess
from pathlib import Path

import click

_CURRENT_MOD_RE = re.compile(r'<div class="currentmodule">([^<]+)<\/div>\s*', flags=re.MULTILINE)
_REFERENCE_RE = re.compile(r'<span class="title-ref">([^<]+)<\/span>', flags=re.MULTILINE)


def fix_references(file: str, *, module: str | None, **kwargs) -> str:
    """Fix API references.

    Pandoc isn't

    """
    # Find `currentmodule` statements
    current_mod = [(m[1].strip(), m.end()) for m in _CURRENT_MOD_RE.finditer(file)]
    if not current_mod and module:
        # Without a currentmodule directive Sphinx still defaults to the root module
        current_mod = [(module, 0)]

    def sub_ref(m: re.Match) -> str:
        qualname: str = m[1].strip()
        name = qualname

        if qualname.startswith("~"):
            # Ref starting with ~ means that the link text should be just the last part of the path
            qualname = qualname[1:]
            _, _, name = qualname.rpartition(".")

        qualname = qualname.removesuffix("()")

        basemod, _, _ = qualname.partition(".")
        # If the root module of the ref can't be imported see if there's a valid prefix
        if not _can_import(basemod):
            for curmod, idx in reversed(current_mod):
                # Find most recent `currentmodule` directive before this ref
                if idx < m.start():
                    if _can_import(f"{curmod}.{basemod}"):
                        qualname = f"{curmod}.{qualname}"

                    break

        return f"[`{name}`][{qualname}]"

    file = _REFERENCE_RE.sub(sub_ref, file)
    # Remove residual `currentmodule` statements
    return _CURRENT_MOD_RE.sub("", file)


def _can_import(path: str) -> bool:
    try:
        _ = importlib.import_module(path)
    except ImportError:
        basemod, _, obj = path.rpartition(".")
        if not basemod:
            return False

        try:
            m = importlib.import_module(basemod)
            return hasattr(m, obj)
        except ImportError:
            return False
    else:
        return True


_ADMONITION_RE = re.compile(r"> \[!([a-zA-Z]+)\]\s*((?:> ?[^\n]*\n)+)", flags=re.MULTILINE)


def fix_admonitions(file: str, **kwargs) -> str:
    """Convert admonitions to the format expected by mkdocs."""

    def sub_admonition(m: re.Match) -> str:
        kind: str = m[1]
        lines: str = m[2]
        block = re.sub(r"> ?", r"\t", lines)
        return f"!!! {kind.lower()}\n{block}"

    return _ADMONITION_RE.sub(sub_admonition, file)


_PYCON_FENCE_RE = re.compile(r"```[a-zA-Z ]*\n>>>", flags=re.MULTILINE)
_PYCON_END_RE = re.compile(r"^((?:>>>|\.\.\.) .+?$\n)```", flags=re.MULTILINE)


def fix_pycon_blocks(file: str, **kwargs) -> str:
    # Find fenced code blocks containing `>>>` lines and mark them as `pycon`
    file = _PYCON_FENCE_RE.sub("```pycon\n>>>", file)
    # Ensure pycon blocks have a final output line
    return _PYCON_END_RE.sub(r"\g<1>\n```", file)


_TITLE_RE = re.compile(r"^---\s+^title: (.+)\s^---", flags=re.MULTILINE)
_HEADER_RE = re.compile(r"^(#+) \b", flags=re.MULTILINE)


def title_to_header(file: str, **kwargs) -> str:
    """Fix incorrect header levels.

    Check if file has a `title` frontmatter entry.
    If so add it as a level 1 header and shift all other headers down a level.
    Some markdown processors treat `title` as a header but mkdocs does not.
    """
    parts = _TITLE_RE.split(file, maxsplit=1)
    if len(parts) > 1:
        file = f"# {parts[1]}" + _HEADER_RE.sub(r"#\g<1> ", parts[2])
    return file


_LINEBREAK_RE = re.compile(
    r"(?<=\n\n)(?!```|- |\* |!!!|\?\?\?|#|\[\]|> )([^\n].+?\n){2,}(?=\n|\Z)",
    flags=re.MULTILINE,
)
_FENCE_RE = re.compile(r"^```.+?^```\n", flags=re.MULTILINE | re.DOTALL)


def fix_whitespace(file: str, **kwargs) -> str:
    """This function attempts to find and remove non-rendering newlines to make files more readable.

    RST files use manual linebreaks while markdown has automatic line wrapping.
    Pandoc keeps all newlines when converting which results in lots of fragmented lines.

    Note that this function takes a conservative approach to determining safe newlines to remove.
    In particular, it does not process newlines that are part of bulleted lists.
    """
    fences = [(m.start(), m.end()) for m in _FENCE_RE.finditer(file)]

    def sub_newline(m: re.Match) -> str:
        for fence in fences:
            if m.start() <= fence[1] and m.end() >= fence[0]:
                return m[0]

        return re.sub("\n", " ", m[0]) + "\n"

    return _LINEBREAK_RE.sub(sub_newline, file)


# List of transforms to apply to each file after RST->MD conversion
TRANSFORMS = [
    title_to_header,
    fix_references,
    fix_admonitions,
    fix_pycon_blocks,
    fix_whitespace,
]


def process_file(src: Path, dst: Path, dry_run: bool, module: str | None) -> None:
    print(f"{src} -> {dst}")
    if dry_run:
        return

    # Convert input from RST to markdown using pandoc
    # Github-flavored markdown seems to produce slightly better results
    subprocess.run(["pandoc", "-s", "--read=rst", "--write=gfm", "-o", str(dst), str(src)], check=True)  # noqa: S603, S607

    # Read file, apply transforms, then write back out
    txt = dst.read_text()
    for tfm in TRANSFORMS:
        txt = tfm(txt, module=module)
    dst.write_text(txt)


def expand_paths(src: Path):
    if src.is_dir():
        for path in src.rglob("*.rst"):
            yield (path, path.relative_to(src))
    else:
        yield (src, Path(src.name))


@click.command
@click.argument("sources", nargs=-1, type=click.Path(path_type=Path, exists=True))
@click.option("-o", "--out", type=click.Path(path_type=Path))
@click.option("--dry-run", is_flag=True)
@click.option("-m", "--module", type=str, default=None)
def main(sources: tuple[Path], out: Path, dry_run: bool, module: str | None):
    out_is_dir = out.is_dir() or not (out.exists() or out.suffix)
    files = [s for src in sources for s in expand_paths(src)]

    if not out_is_dir:
        if len(files) > 1:
            msg = "Multiple input files specified but output is not a directory"
            raise RuntimeError(msg)

        process_file(files[0][0], out, dry_run, module)
        return

    for src, dst in files:
        dst = (out / dst).with_suffix(".md")
        process_file(src, dst, dry_run, module)


if __name__ == "__main__":
    main()
