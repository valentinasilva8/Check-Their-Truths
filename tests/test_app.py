"""The /chat tool record keeps the starter's field names."""

from app import run_agent


class _Function:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class _Call:
    def __init__(self):
        self.id = "call-1"
        self.function = _Function("list_cases", "{}")


class _Message:
    def __init__(self, content, tool_calls):
        self.content = content
        self.tool_calls = tool_calls

    def model_dump(self):
        return {"role": "assistant", "content": self.content}


class _Reply:
    def __init__(self, message):
        self.choices = [type("Choice", (), {"message": message})()]


def test_every_tool_call_has_name_args_and_result(monkeypatch):
    seen = {"n": 0}

    def fake_completion(**kwargs):
        seen["n"] += 1
        if seen["n"] == 1:
            return _Reply(_Message(None, [_Call()]))
        return _Reply(_Message("Done.", None))

    monkeypatch.setattr("app.litellm.completion", fake_completion)
    text, tool_calls = run_agent([{"role": "user", "content": "hello"}])

    assert text == "Done."
    assert len(tool_calls) == 1
    assert set(tool_calls[0]) == {"name", "args", "result"}
    assert tool_calls[0]["name"] == "list_cases"
    assert tool_calls[0]["args"] == {}
    assert "cases" in tool_calls[0]["result"]
