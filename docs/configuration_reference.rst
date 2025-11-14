============================
UD2 Configuration Reference
============================

The UD2 CLI reads its connection details from an INI-formatted configuration
file. Each section in the file represents an environment profile (for example
``dev`` or ``prod``) that can be selected on the command line with ``--env``.


Configuration File Location
===========================

The CLI searches for the configuration file in the following order:

1. The path supplied with ``--config`` on the command line.
2. ``$UD2_CONFIG`` if the environment variable is set.
3. The default user configuration path ``~/.config/ud2/config.ini``.

Use ``ud2 --show-config-path`` to confirm where the tool expects to find the
file. If you maintain multiple configuration files, reference the appropriate
one with ``--config`` when running commands.


Configuration Sections
======================

Every environment section must provide connection details for the Unified
Downloads API. Section names map directly to the value passed with ``--env``.
The CLI will raise an error if the requested section is missing.


Required Options
================

``base_url``
   Fully-qualified URL for the UD2 API endpoint.

``client_cert``
   Absolute or user-relative path to the client TLS certificate file (``.crt``,
   ``.pem``, etc.). The CLI expands ``~`` and resolves relative paths.

``client_key``
   Absolute or user-relative path to the private key paired with
   ``client_cert``.


Optional Options
================

``timeout``
   Socket timeout in seconds. Non-numeric values are ignored and the CLI will
   fall back to the default behavior (no explicit timeout).

``verify``
   Controls TLS certificate validation. Accepts truthy strings such as
   ``true``, ``yes``, or ``1`` to enable validation. Set to ``false`` to
   disable verification (not recommended outside of controlled testing
   environments).


Example Configuration
=====================

The sample below demonstrates two environments in a single configuration file.
The `dev` section connects to a staging API and disables certificate
verification, while `prod` points to the production endpoint and enforces strict
TLS settings.

.. code-block:: ini

   [main]
   # the default environment to use if --env is not specified.
   default = dev

   [DEFAULT]
   # these options apply to all environments unless overridden.
   timeout = 5
   verify = true

   [dev]
   base_url = https://staging.downloads.example.com/api/v1
   client_cert = ~/.config/ud2/certs/dev-client.crt
   client_key = ~/.config/ud2/certs/dev-client.key
   verify = false

   [prod]
   base_url = https://downloads.example.com/api/v1
   client_cert = ~/.config/ud2/certs/prod-client.crt
   client_key = ~/.config/ud2/certs/prod-client.key

Select an environment when running commands:

.. code-block:: bash

   ud2 --env prod products list


Troubleshooting
===============

``Environment 'X' not found``
   The selected environment does not exist in the configuration file. Confirm
   the section name and spelling.

``Configuration file not found or unreadable``
   The CLI could not open the file at the resolved location. Check permissions
   and paths, especially when using a custom ``--config`` value.

``Invalid timeout value``
   The timeout value could not be parsed as a floating point number. Update the
   option with a numeric value (for example ``5`` or ``2.5``).


Next Steps
==========

* Pair this reference with the quickstart scenarios to see how configuration
  choices affect typical release workflows.
* Store sensitive credentials (such as ``client_key``) with restricted
  filesystem permissions to prevent accidental disclosure.
* Use separate sections for automation accounts to isolate credentials from
  developer logins.


.. The end.
