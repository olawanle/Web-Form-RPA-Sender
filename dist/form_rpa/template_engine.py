from __future__ import annotations

from typing import Dict

from jinja2 import Environment, FileSystemLoader, StrictUndefined


def build_salutation(contact_name: str | None, honorific: str = "Mr./Ms.") -> str:
	name = (contact_name or "").strip()
	if name:
		return f"{honorific} {name}"
	return "Sir/Madam"


def render_template(template_path: str, context: Dict[str, object]) -> str:
	loader = FileSystemLoader(searchpath=".")
	env = Environment(loader=loader, undefined=StrictUndefined, autoescape=False)
	dir_path, file_name = "/".join(template_path.split("/")[:-1]) or ".", template_path.split("/")[-1]
	env.loader = FileSystemLoader(searchpath=dir_path)
	template = env.get_template(file_name)
	return template.render(**context)
