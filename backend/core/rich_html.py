"""Sanitise author-written rich text before it is shown to other users.

Trainers format course text in a WYSIWYG editor (Report 8 #8/#9/#17); the
HTML is rendered to students, so anything beyond formatting markup (scripts,
event handlers, iframes, javascript: URLs, arbitrary CSS) is stripped here,
at save time, for every consumer.
"""

import re

import nh3

_TAGS = {
    "p", "br", "strong", "b", "em", "i", "u", "s", "span", "h1", "h2", "h3",
    "ul", "ol", "li", "a", "img", "blockquote", "code", "pre", "hr",
}  # fmt: skip
_ATTRIBUTES = {
    "a": {"href", "title", "target"},
    "img": {"src", "alt", "width", "height"},
    "*": {"style"},
}
_STYLES = {"color", "background-color", "font-size", "text-align", "font-family"}
_LOOKS_LIKE_HTML = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")


def _attribute_filter(tag: str, attr: str, value: str):
    # data: URLs only for embedded images, never for links.
    if tag == "a" and attr == "href" and value.strip().lower().startswith("data:"):
        return None
    return value


def sanitize_rich_html(value: str) -> str:
    """Clean HTML; plain text (no tags) is returned unchanged."""
    if not value or not _LOOKS_LIKE_HTML.search(value):
        return value
    return nh3.clean(
        value,
        tags=_TAGS,
        attributes=_ATTRIBUTES,
        filter_style_properties=_STYLES,
        url_schemes={"http", "https", "mailto", "data"},
        attribute_filter=_attribute_filter,
    )
