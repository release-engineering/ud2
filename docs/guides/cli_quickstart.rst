============================
UD2 CLI Quickstart Scenarios
============================

This guide walks through the core ``ud2`` command-line workflows you will use
when preparing a new release: creating a product record, adding versions, and
attaching downloadable files. Each section is self-contained so you can follow
along in sequence or jump straight to the scenario you need.


Prerequisites
=============

* ``ud2`` is installed and available on your ``PATH`` (``ud2 --version`` should
  succeed).
* Your UD2 configuration file is accessible (defaults to
  ``~/.config/ud2/config.ini``). Use ``--config`` or ``--env`` if you need to
  override the defaults.
* You can reach the Unified Downloads API from the machine running the CLI.

All examples below use the default "friendly" output, which renders tabular data
for easy scanning. Switch to YAML with ``--yaml`` if you prefer machine
readable results.


Scenario 1: Create a Product
============================

1. Draft a YAML payload describing the product. Save the file as
   ``product.yaml``.

   .. code-block:: yaml

      eng_id: 4001
      name: "Project Atlas"
      arch: x86_64
      category: "Platform"
      product_code: atlas
      product_group: "Atlas"
      product_group_name: "Project Atlas"

2. Create the product in UD2.

   .. code-block:: bash

      ud2 product create --yaml-file product.yaml

   The CLI prints the new product record. Take note of the ``Id`` field; you
   will reference it when creating versions. You can retrieve the product again
   at any time:

   .. code-block:: bash

      ud2 product get 4001


Scenario 2: Add a Version
=========================

1. Capture the version payload in ``version.yaml``. The ``visibility`` value
   accepts any server-supported enum (for example ``private`` or ``public``).

   .. code-block:: yaml

      version: "1.0"
      architecture: x86_64
      cpe: "cpe:/o:example:atlas_os:1.0"
      platform: "linux"
      visibility: public

2. Create the version, passing the product identifier reported earlier.

   .. code-block:: bash

      ud2 version create 4001 --yaml-file version.yaml

   Record the returned version ``Id``; you will need it when associating files.
   You can list all versions for the product whenever you need to confirm IDs:

   .. code-block:: bash

      ud2 version list 4001


Scenario 3: Attach Release Files
================================

Files are represented as repositories in UD2. Create one repository entry per
deliverable you intend to publish.

1. Describe the file in ``repository.yaml``.

   .. code-block:: yaml

      description: "Atlas 1.0 GA ISO"
      fileName: atlas-1.0-ga.iso
      fileSize: 734003200
      sha256: "1f2d3c4b5a69788766554433221100ffeeddccbbaa99887766554433221100ff"
      contentTypes:
        - application/x-iso9660-image

2. Attach the file to the version using its identifier.

   .. code-block:: bash

      ud2 repository create 101 --yaml-file repository.yaml

   The output includes the repository ``Id``. Repeat the process with distinct
   payload files to associate additional artifacts (for example debug symbols or
   container images) with the same version.

   Alternatively, use ``--file`` to reference the artifact on disk; the CLI will
   derive ``fileName``, ``fileSize``, ``sha256``, and ``md5`` automatically:

   .. code-block:: bash

      ud2 repository create 101 --file ./atlas-1.0-ga.iso --description "Atlas 1.0 GA ISO"


Scenario 4: Locate an Existing Version
======================================

When you need to add files to an existing version or double-check its metadata,
list the known versions and filter for the one you need.

.. code-block:: bash

   ud2 version list 4001

Add ``--yaml`` to pipe the structured data through tools such as ``yq``
or ``jq`` if you prefer automated filtering:

.. code-block:: bash

   ud2 version list 4001 --yaml | yq '.[] | select(.version == "1.0")'

The friendly output also includes the version ``Id``, which you will use in the
next scenario when adding more files.


Scenario 5: Add More Files to a Version
=======================================

After locating the version identifier, prepare another repository payload (for
example ``repository-debug.yaml``) describing the additional file.

.. code-block:: yaml

   description: "Atlas 1.0 Debug Symbols"
   fileName: atlas-1.0-debug.tar.gz
   fileSize: 189792256
   sha256: "ffeeddccbbaa0099887766554433221100ffeeddccbbaa009988776655443322"

Use the same ``ud2 repository create`` command, passing the version identifier
and the new YAML file.

.. code-block:: bash

   ud2 repository create 101 --yaml-file repository-debug.yaml

You can confirm the inventory of files attached to a version by listing the
repositories. Pagination options are available for large sets.

.. code-block:: bash

   ud2 repository list 101 --limit 20


Scenario 6: Fix a Typographical Error in a File Title
=====================================================

Suppose a repository description contains a typo and needs an update. Retrieve
the current record, write a corrected payload, and submit it with ``update``.

1. Fetch the repository to get its ``Id`` and current fields.

   .. code-block:: bash

      ud2 repository get 205

2. Copy the output into ``repository-corrected.yaml`` and adjust the fields that
   need fixing. For example, correcting the description spelling:

   .. code-block:: yaml

      description: "Atlas 1.0 Debug Symbols"
      fileName: atlas-1.0-debug.tar.gz
      fileSize: 189792256
      sha256: "ffeeddccbbaa0099887766554433221100ffeeddccbbaa009988776655443322"

3. Apply the update with the version and repository identifiers.

   .. code-block:: bash

      ud2 repository update 205 --yaml-file repository-corrected.yaml

The CLI confirms success and prints the updated repository. If you only need to
verify the change, re-run ``ud2 repository get`` after the update.


Next Steps
==========

* For manifest-based release workflows (check and push), see
  :doc:`release_quickstart`.
* Explore pagination flags (``--page`` / ``--limit``) on list commands for large
  result sets.
* Switch to YAML output (``--yaml``) to integrate UD2 workflows with automation
  or CI pipelines.
* Use ``ud2 --help`` and command-specific ``--help`` flags to discover advanced
  options.

.. The end.
