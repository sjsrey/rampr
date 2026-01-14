def test_import():
    import rampr
    import rampr.datasets as ds

    assert hasattr(rampr, "__version__")
    assert isinstance(ds.list_datasets(), dict)
