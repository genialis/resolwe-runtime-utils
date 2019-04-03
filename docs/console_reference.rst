Console reference
-----------------

List of console commands that can be used inside a Bash Resolwe process.

.. describe:: re-save

    A console wrapper for :func:`resolwe_runtime_utils.save`.

.. describe:: re-export

    A console wrapper for :func:`resolwe_runtime_utils.export_file`.

.. describe:: re-save-list

    A console wrapper for :func:`resolwe_runtime_utils.save_list`.

.. describe:: re-save-file

    A console wrapper for :func:`resolwe_runtime_utils.save_file`.

.. describe:: re-save-file-list

    A console wrapper for :func:`resolwe_runtime_utils.save_file_list`.

.. describe:: re-save-dir

    A console wrapper for :func:`resolwe_runtime_utils.save_dir`.

.. describe:: re-save-dir-list

    A console wrapper for :func:`resolwe_runtime_utils.save_dir_list`.

.. describe:: re-info

    A console wrapper for :func:`resolwe_runtime_utils.info`.

.. describe:: re-warning

    A console wrapper for :func:`resolwe_runtime_utils.warning`.

.. describe:: re-error

    A console wrapper for :func:`resolwe_runtime_utils.error`.

.. describe:: re-progress

    A console wrapper for :func:`resolwe_runtime_utils.progress`.

.. describe:: _re-checkrc

    A console wrapper for :func:`resolwe_runtime_utils.checkrc`.

    .. note::

        It should not be used directly. Instead, create a wrapper Bash function
        that calls it with the return value of the previously executed Bash
        command::

            re-checkrc() { _re-checkrc $? "$@"; }

        Add the following snippet to your ``~/.bash_profile`` and/or
        ``~/.bashrc`` file to make it easily accessible.
