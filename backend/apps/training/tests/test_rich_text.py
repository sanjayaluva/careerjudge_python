"""Rich text for training text content is sanitised (Report 8 #8/#9/#17)."""

from core.rich_html import sanitize_rich_html


def test_formatting_survives():
    html = (
        "<h2>Intro</h2><p><strong>Bold</strong> <em>it</em> <u>u</u> "
        '<span style="color: #d00; font-size: 18px">red</span></p>'
        '<ul><li>one</li></ul><p style="text-align: center">c</p>'
        '<img src="https://x.test/a.png" alt="a">'
    )
    out = sanitize_rich_html(html)
    for keep in ("<h2>", "<strong>", "<em>", "<u>", "color", "font-size", "<ul>", "text-align",
                 "<img"):  # fmt: skip
        assert keep in out, keep


def test_dangerous_markup_is_removed():
    out = sanitize_rich_html(
        '<p onclick="x()">hi</p><script>alert(1)</script><iframe src="//e"></iframe>'
        '<a href="javascript:alert(1)">j</a><a href="data:text/html,x">d</a>'
        '<span style="position:fixed;color:red">s</span>'
    )
    assert "onclick" not in out and "<script" not in out and "<iframe" not in out
    assert "javascript:" not in out and "data:text" not in out
    assert "position" not in out and "color:red" in out.replace(" ", "")


def test_plain_text_is_untouched():
    text = "Introduction\n\nStep 1 < Step 2 & more"
    assert sanitize_rich_html(text) == text
