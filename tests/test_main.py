from second_brain.main import main


def test_main(capsys):
    main()
    captured = capsys.readouterr()
    assert captured.out == "Hello from second-brain!\n"
