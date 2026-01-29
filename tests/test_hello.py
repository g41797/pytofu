from pytofu import main


def test_main(capsys):
    """Test that main prints 'Hello tofu'."""
    main()
    captured = capsys.readouterr()
    assert captured.out.strip() == "Hello tofu"
