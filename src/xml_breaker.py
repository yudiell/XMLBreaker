"""Module for breaking down XML files."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from lxml import etree

if TYPE_CHECKING:
    from collections.abc import Iterable

    from logbook import Logger


class XmlBreaker:
    """Class for breaking down XML files."""

    def __init__(self: XmlBreaker, etree: etree, xml: bytes, logger: Logger) -> None:
        """Initialize XmlBreaker."""
        if not xml:
            raise ValueError("XML bytes content is required.")
        self.logger = logger
        self.etree = etree
        self.tree = self.etree.fromstring(text=xml)
        self.root = self.tree.getroottree()
        self.elements = self.root.iter()

    def write_xml(self: XmlBreaker, element: etree.Element, file_path: str) -> None:
        """Write XML to a file."""
        if not file_path:
            raise ValueError("File path is required.")
        with Path(file_path).open("wb") as f:
            element.write(f, encoding="utf-8", xml_declaration=True, pretty_print=True)

    def get_element_by_tag(
        self: XmlBreaker, tag: str, elements: Iterable[etree.Element]
    ) -> etree.Element:
        """Get element by tag."""
        if not tag:
            raise ValueError("Tag is required.")
        if not elements:
            raise ValueError("Parent element is required.")
        for element in elements:
            if element.tag == tag:
                return element
        self.logger.error(f"Element with tag {tag=} not found.")

    def split_records(
        self: XmlBreaker,
        element: etree.Element,
        number_of_records: int = 250,
        display_messages: bool = False,
    ) -> list[etree.Element]:
        """Split records into chunks."""
        if element is None:
            raise ValueError("Element is required.")
        if type(element) is not etree._Element:
            raise ValueError(
                "element must be an instance of"
                f"etree.Element. Received {type(element)}"
            )
        xmls = []
        records = element.getchildren()
        if display_messages:
            self.logger.info(f"{len(records)} records found in {element}.")
        chunked = [
            records[i : i + number_of_records]
            for i in range(0, len(records), number_of_records)
        ]
        for chunk in chunked:
            element.clear()
            for record in chunk:
                element.append(record)
            if display_messages:
                self.logger.info(
                    f"{len(element.getchildren())} records in element {element}."
                )
            xmls.append(element.getroottree().__deepcopy__(memo={}))
        return xmls
