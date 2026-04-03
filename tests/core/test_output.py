from __future__ import annotations


def test_safe_print_is_exported_from_core_output():
    from cogstash.core.output import safe_print

    assert callable(safe_print)


def test_core_output_does_not_export_cli_stream_helpers():
    import cogstash.core.output as output

    assert not hasattr(output, "stream_is_interactive")
    assert not hasattr(output, "stream_supports_color")


def test_output_shim_re_exports_all_symbols():
    from cogstash._output import safe_print, stream_is_interactive, stream_supports_color

    assert callable(safe_print)
    assert callable(stream_is_interactive)
    assert callable(stream_supports_color)
