============================
UD2 CLI Quickstart Scenarios
============================

This guide walks through the core ``ud2`` command-line workflows you will use
when preparing a new release: creating a product record, adding versions,
attaching downloadable files, and deleting those resources safely. Each section
is self-contained so you can follow along in sequence or jump straight to the
scenario you need.


Prerequisites
=============

* ``ud2`` is installed and available on your ``PATH`` (``ud2 --help`` should
  succeed).
* Your UD2 configuration file is accessible (defaults to
  ``~/.config/ud2/config.ini``). Use ``--config`` or ``--env`` if you need to
  override the defaults.
* You can reach the Unified Downloads API from the machine running the CLI.


List output ordering
====================

``ud2 product list``, ``ud2 version list <product-id>``, and
``ud2 repository list <version-id>`` show rows in ascending resource ID order by
default. ``product list`` and ``repository list`` accept ``--sort asc`` (the
default) or ``--sort desc`` to request the corresponding order from the API.
``version list`` has no ``--sort`` option; the CLI sorts versions by ID after
the response is returned. That behavior is separate from the optional
``sort_version`` field on a product version resource (set with ``--sort-version``
on ``version create`` or ``version update``), which the API uses for version
ordering rules.


All examples below use the default "friendly" output, which renders tabular data
for easy scanning. Switch to YAML with ``--yaml`` if you prefer machine
readable results.


Scenario 1: Create a Product
============================

Create the product using command-line switches:

.. code-block:: bash

   ud2 product create --name "Project Atlas" --eng-id 4001 --arch x86_64 \
     --category "Platform" --product-code atlas --product-group "Atlas" \
     --product-group-name "Project Atlas"

The CLI prints the new product record. Take note of the ``Id`` field; you will
reference it when creating versions. You can retrieve the product again at any
time:

.. code-block:: bash

   ud2 product get 4001

Use ``--yaml-file`` if you prefer to load the payload from a file for complex
or repeated configurations.


Scenario 2: Add a Version
=========================

Create the version using command-line switches, passing the product identifier
reported earlier. The ``--visibility`` value accepts any server-supported enum
(for example ``private`` or ``public``):

.. code-block:: bash

   ud2 version create 4001 --version "1.0" --architecture x86_64 \
     --cpe "cpe:/o:example:atlas_os:1.0" --platform "linux" --visibility public

Add ``--sort-version`` when the API should use a dedicated string for ordering
(for example ``8.5.0``) alongside the display ``--version`` string. Use
``ud2 version update <version-id> --sort-version ...`` to change it later.

Record the returned version ``Id``; you will need it when associating files.
You can list all versions for the product whenever you need to confirm IDs:

.. code-block:: bash

   ud2 version list 4001

Use ``--yaml-file`` if you prefer to load the payload from a file.


Scenario 3: Attach Release Files
================================

Files are represented as repositories in UD2. Create one repository entry per
deliverable you intend to publish. Use ``--file`` to reference the artifact on
disk; the CLI derives ``fileName``, ``fileSize``, ``sha256``, and ``md5``
automatically:

.. code-block:: bash

   ud2 repository create 101 --file ./atlas-1.0-ga.iso \
     --description "Atlas 1.0 GA ISO" --content-type DISTRIBUTION

The output includes the repository ``Id``. Repeat with distinct artifacts to
associate additional files (for example debug symbols or container images) with
the same version. Use ``--yaml-file`` if you need to supply a full payload from
a file.


Scenario 4: Locate an Existing Version
======================================

When you need to add files to an existing version or double-check its metadata,
use search or list commands.

To find a product by name or engineering ID:

.. code-block:: bash

   ud2 product search --name "Atlas"
   ud2 product search --eng-id 4001

To search for a specific version across products or filter by criteria:

.. code-block:: bash

   ud2 version search --product-id 4001 --version "1.0"

To list all versions for a product you already know:

.. code-block:: bash

   ud2 version list 4001

Add ``--yaml`` to pipe the structured data through tools such as ``yq`` or
``jq`` for automated filtering. The output includes the version ``Id``, which
you will use when adding more files.


Scenario 5: Add More Files to a Version
=======================================

After locating the version identifier, add another file using ``--file`` and
``--description``:

.. code-block:: bash

   ud2 repository create 101 --file ./atlas-1.0-debug.tar.gz \
     --description "Atlas 1.0 Debug Symbols" --content-type DISTRIBUTION

You can confirm the inventory of files attached to a version by listing the
repositories. Pagination options are available for large sets:

.. code-block:: bash

   ud2 repository list 101 --limit 20


Scenario 6: Fix a Typographical Error in a File Title
=====================================================

Suppose a repository description contains a typo and needs an update. Apply the
correction using ``--desc``. The update command fetches the existing record and
merges only the changed field(s):

.. code-block:: bash

   ud2 repository update 205 --desc "Atlas 1.0 Debug Symbols"

The CLI confirms success and prints the updated repository. To verify the
change, re-run ``ud2 repository get 205``.


Deleting resources
==================

``ud2 product delete``, ``ud2 version delete``, and ``ud2 repository delete`` are
interactive by default. Each command loads the target record from the API, prints
a short plain-text summary (independent of global ``--yaml`` output), and asks:

``Delete this entry? [y/N]``. The default is **no**; only an explicit ``y``
continues to the delete request.

Pass ``--force`` to skip the confirmation prompt. ``--force`` does **not**
override dependency checks on product or version deletes:

* **Product:** deletion is refused if any product versions still exist for that
  product. Remove those versions (after their files are gone) before deleting
  the product.
* **Version:** deletion is refused if any repository (file) records are still
  attached to that version. Remove those files first.
* **Repository (file):** there is no dependency check; ``--force`` only skips
  the prompt.

When a delete is blocked by existing child resources, the CLI prints an error
that includes a count and does not call the delete API.

.. code-block:: bash

   # Prompted after a short preview (answer y or n)
   ud2 repository delete 205

   # No prompt; still loads the record first
   ud2 repository delete 205 --force

   # Fails if the product still has versions
   ud2 product delete 4001

   # Fails if the version still has repository files
   ud2 version delete 101


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
* See **Deleting resources** for interactive deletes, ``--force``, and when
  product or version removal is blocked by existing child records.

Using YAML Files
================

All create and update commands support ``--yaml-file`` for loading payloads from
a file. Use this when you prefer file-based workflows, need complex payloads, or
want to reuse configurations. See :doc:`configuration_reference` for connection
and environment setup.

.. The end.
