Moving JWST code to github
==========================

What to move from SVN to github
-------------------------------

jwst_lib:
    - stpipe
    - models
    - pipeline_models (rename these to transforms)
    - astdata?
    - fits_extensions?

jwst_pipeline:
    - everything except bias_drift

jwsttools:
    - assocations
    - fits_generator
    - csv_tools
    - timeconversion

    - nircam_mosaic?
    - don't transfer spectools

How to organize the code
------------------------

Installation structure
++++++++++++++++++++++

Whatever is decided, at the all JWST pipeline code should be installable by one command.

    1. Keep it as it is
       There was a general dislike of namespaces and the nested directory structure we have to
       use currently.

    2. Install all JWST code under one directory, e.g.

        jwst
             stpipe
             models
             bias_drift
             other steps
             ...
             tools packages

        Note: stpipe and models maybe used as standalone packages by other projects (WFIRST?)
        Should we keep them in a common jwst/ directory or is it better to package them
        as separate packages?

        How about the jwst_tools packages? Are they general data analysis tools or are they
        JWST specific?


Github organization
+++++++++++++++++++

    1. Keep things as they are - 3 repos ,jwst_lib, jwst_pipeline, jwst_tools. This was not
       a popular option.

    2. Have all jwst code in one repo mimicking the installaiton structure in 2 above.
       Same Note as above applies here.

       Advantages:

       This has the advantage of having common Travis CI tests which run on every PR to test the
       integrity of the pipeline, i.e. it's easier to handle dependencies between steps by having
       tests that run the entire pipeline.

       This also allows the entire pipeline to have one version making it easier to debug user
       configuration and environments.

       Disadvantages:

       Everyone has write permissions to the main repository. If we really agree on assigning a
       primary and secondary mainteiner to each step (see below), they all have merge right to
       the entire repo. In reality it's unlikely this to be a major problem and a bit of communication
       will solve any issues.


    3. Have every step and jwst_lib subpackage in a separate repo.

       This does not have the disadvantage listed in 2. above.

       Every step will have its own version -is this good or bad?
       (I vote for bad.)


# 2 was the preferred option among those present.


SSBDEV build
------------

  When we move to astroconda there will be no SSBDEV build as we know it now.
  Everyone will have to install anaconda locally and then install astroconda-dev.
  astroconda-dev pulls code from the master branch of all repositories on github

Workflow
--------

Joe wrote a good "Starting with github" document (https://confluence.stsci.edu/display/SSB/Github+and+You

JWST workflow - like astropy use pull requests and don't merge directly to the
repository.

http://astropy.readthedocs.io/en/latest/development/workflow/maintainer_workflow.html

- Have (at least) two maintainers for each subpackage - they are the ones who
  can merge a PR to a subpackage.

- Do pre-commit reviews - do not merge without someone else looking at the PR

- Use Travis CI to test PRs -

  - Have a PEP8 check run on all PRs. This will prevent simple errors going into
    a build.
  - If possible add unit tests to each subpackage.
  - Each step subpackage should have at least some minimal tests of dependencies, e.g. make
    sure the dependencies are importable.


We did not have time to discuss documentation and releases.