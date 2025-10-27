"""Module for breaking down XML files."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from lxml import etree

if TYPE_CHECKING:
    from collections.abc import Iterable


class XmlBreaker:
    """Class for breaking down XML files."""

    def __init__(self, xml: bytes, logger: logging.Logger) -> None:
        """Initialize XmlBreaker."""
        if not xml:
            raise ValueError("XML bytes content is required.")
        
        self.logger = logger
        self.root = etree.fromstring(xml)

    def write_xml(self, element: etree._Element, file_path: str | Path) -> None:
        """Write XML to a file."""
        if not file_path:
            raise ValueError("File path is required.")
        
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        tree = etree.ElementTree(element)
        with path.open("wb") as f:
            tree.write(
                f,
                encoding="utf-8",
                xml_declaration=True,
                pretty_print=True
            )

    def get_element_by_tag(
        self,
        tag: str,
        elements: Iterable[etree._Element]
    ) -> etree._Element | None:
        """Get element by tag."""
        if not tag:
            raise ValueError("Tag is required.")
        if not elements:
            raise ValueError("Elements iterable is required.")
        
        for element in elements:
            if element.tag == tag:
                return element
        
        self.logger.error(f"Element with tag {tag=} not found.")
        return None

    def split_records(
        self,
        element: etree._Element,
        number_of_records: int = 250,
        display_messages: bool = False,
    ) -> list[etree._ElementTree]:
        """Split records into chunks."""
        if element is None:
            raise ValueError("Element is required.")
        
        if not isinstance(element, etree._Element):
            raise TypeError(
                f"element must be an lxml Element. Received {type(element)}"
            )
        
        records = list[Any](element) 
        
        if display_messages:
            self.logger.info(f"{len(records)} records found in element.")
        
        chunks = [
            records[i : i + number_of_records]
            for i in range(0, len(records), number_of_records)
        ]
        
        xmls = []
        for chunk in chunks:
            new_element = etree.Element(element.tag, attrib=element.attrib)
            new_element.text = element.text
            new_element.tail = element.tail
            
            for record in chunk:
                new_element.append(record)
            
            if display_messages:
                self.logger.info(f"{len(new_element)} records in chunk.")
            
            xmls.append(etree.ElementTree(new_element))
        
        return xmls