"""Tests for XmlBreaker module."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pytest
from lxml import etree

from xml_breaker import XmlBreaker  # Adjust import based on your module name


# Fixtures
@pytest.fixture
def logger():
    """Create a test logger."""
    return logging.getLogger("test_logger")


@pytest.fixture
def simple_xml():
    """Simple XML for basic testing."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<root>
    <item id="1">Item 1</item>
    <item id="2">Item 2</item>
    <item id="3">Item 3</item>
</root>"""


@pytest.fixture
def complex_xml():
    """More complex XML with multiple element types."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<catalog>
    <books>
        <book id="1">
            <title>Book 1</title>
            <author>Author 1</author>
        </book>
        <book id="2">
            <title>Book 2</title>
            <author>Author 2</author>
        </book>
        <book id="3">
            <title>Book 3</title>
            <author>Author 3</author>
        </book>
    </books>
    <magazines>
        <magazine id="1">Magazine 1</magazine>
    </magazines>
</catalog>"""


@pytest.fixture
def large_xml():
    """XML with many records for testing splitting."""
    items = "\n".join([f'    <record id="{i}">Record {i}</record>' for i in range(1, 501)])
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<records>
{items}
</records>""".encode("utf-8")


@pytest.fixture
def xml_breaker(simple_xml, logger):
    """Create an XmlBreaker instance."""
    return XmlBreaker(xml=simple_xml, logger=logger)


# Test __init__ method
class TestInit:
    """Tests for __init__ method."""

    def test_init_success(self, simple_xml, logger):
        """Test successful initialization."""
        breaker = XmlBreaker(xml=simple_xml, logger=logger)
        assert breaker.logger == logger
        assert breaker.root is not None
        assert breaker.root.tag == "root"

    def test_init_with_empty_bytes(self, logger):
        """Test initialization with empty bytes raises ValueError."""
        with pytest.raises(ValueError, match="XML bytes content is required"):
            XmlBreaker(xml=b"", logger=logger)

    def test_init_with_none(self, logger):
        """Test initialization with None raises ValueError."""
        with pytest.raises(ValueError, match="XML bytes content is required"):
            XmlBreaker(xml=None, logger=logger)

    def test_init_with_invalid_xml(self, logger):
        """Test initialization with malformed XML."""
        invalid_xml = b"<root><unclosed>"
        with pytest.raises(etree.XMLSyntaxError):
            XmlBreaker(xml=invalid_xml, logger=logger)

    def test_init_parses_root_correctly(self, complex_xml, logger):
        """Test that root element is parsed correctly."""
        breaker = XmlBreaker(xml=complex_xml, logger=logger)
        assert breaker.root.tag == "catalog"
        assert len(list(breaker.root)) == 2  # books and magazines


# Test write_xml method
class TestWriteXml:
    """Tests for write_xml method."""

    def test_write_xml_success(self, xml_breaker, tmp_path):
        """Test successful XML writing."""
        output_file = tmp_path / "output.xml"
        xml_breaker.write_xml(xml_breaker.root, str(output_file))
        
        assert output_file.exists()
        
        # Verify content
        tree = etree.parse(str(output_file))
        assert tree.getroot().tag == "root"

    def test_write_xml_creates_directories(self, xml_breaker, tmp_path):
        """Test that parent directories are created."""
        output_file = tmp_path / "nested" / "dir" / "output.xml"
        xml_breaker.write_xml(xml_breaker.root, str(output_file))
        
        assert output_file.exists()
        assert output_file.parent.exists()

    def test_write_xml_with_path_object(self, xml_breaker, tmp_path):
        """Test writing with Path object instead of string."""
        output_file = tmp_path / "output.xml"
        xml_breaker.write_xml(xml_breaker.root, output_file)
        
        assert output_file.exists()

    def test_write_xml_overwrites_existing(self, xml_breaker, tmp_path):
        """Test that existing files are overwritten."""
        output_file = tmp_path / "output.xml"
        
        # Write first time
        xml_breaker.write_xml(xml_breaker.root, str(output_file))
        first_mtime = output_file.stat().st_mtime
        
        # Write again
        xml_breaker.write_xml(xml_breaker.root, str(output_file))
        second_mtime = output_file.stat().st_mtime
        
        assert second_mtime >= first_mtime

    def test_write_xml_with_empty_path(self, xml_breaker):
        """Test writing with empty file path raises ValueError."""
        with pytest.raises(ValueError, match="File path is required"):
            xml_breaker.write_xml(xml_breaker.root, "")

    def test_write_xml_preserves_attributes(self, simple_xml, logger, tmp_path):
        """Test that element attributes are preserved."""
        breaker = XmlBreaker(xml=simple_xml, logger=logger)
        items = list(breaker.root)
        
        output_file = tmp_path / "output.xml"
        breaker.write_xml(items[0], str(output_file))
        
        tree = etree.parse(str(output_file))
        assert tree.getroot().get("id") == "1"

    def test_write_xml_encoding(self, xml_breaker, tmp_path):
        """Test that XML is written with UTF-8 encoding."""
        output_file = tmp_path / "output.xml"
        xml_breaker.write_xml(xml_breaker.root, str(output_file))

        with open(output_file, "rb") as f:
            content = f.read()
            assert b"encoding='UTF-8'" in content


# Test get_element_by_tag method
class TestGetElementByTag:
    """Tests for get_element_by_tag method."""

    def test_get_element_by_tag_found(self, xml_breaker):
        """Test finding an existing element by tag."""
        elements = list(xml_breaker.root)
        result = xml_breaker.get_element_by_tag("item", elements)
        
        assert result is not None
        assert result.tag == "item"

    def test_get_element_by_tag_not_found(self, xml_breaker, caplog):
        """Test searching for non-existent tag."""
        elements = list(xml_breaker.root)
        
        with caplog.at_level(logging.ERROR):
            result = xml_breaker.get_element_by_tag("nonexistent", elements)
        
        assert result is None
        assert "nonexistent" in caplog.text
        assert "not found" in caplog.text

    def test_get_element_by_tag_empty_tag(self, xml_breaker):
        """Test with empty tag raises ValueError."""
        elements = list(xml_breaker.root)
        
        with pytest.raises(ValueError, match="Tag is required"):
            xml_breaker.get_element_by_tag("", elements)

    def test_get_element_by_tag_none_elements(self, xml_breaker):
        """Test with None elements raises ValueError."""
        with pytest.raises(ValueError, match="Elements iterable is required"):
            xml_breaker.get_element_by_tag("item", None)

    def test_get_element_by_tag_empty_list(self, xml_breaker):
        """Test with empty elements list raises ValueError."""
        with pytest.raises(ValueError, match="Elements iterable is required"):
            xml_breaker.get_element_by_tag("item", [])

    def test_get_element_by_tag_returns_first_match(self, xml_breaker):
        """Test that first matching element is returned."""
        elements = list(xml_breaker.root)
        result = xml_breaker.get_element_by_tag("item", elements)
        
        # Should return first item
        assert result.get("id") == "1"

    def test_get_element_by_tag_in_nested_structure(self, complex_xml, logger):
        """Test finding element in nested structure."""
        breaker = XmlBreaker(xml=complex_xml, logger=logger)
        elements = list(breaker.root)
        
        result = breaker.get_element_by_tag("books", elements)
        assert result is not None
        assert result.tag == "books"


# Test split_records method
class TestSplitRecords:
    """Tests for split_records method."""

    def test_split_records_default_chunk_size(self, large_xml, logger):
        """Test splitting with default chunk size of 250."""
        breaker = XmlBreaker(xml=large_xml, logger=logger)
        chunks = breaker.split_records(breaker.root, display_messages=False)
        
        assert len(chunks) == 2  # 500 records / 250 = 2 chunks
        assert isinstance(chunks[0], etree._ElementTree)

    def test_split_records_custom_chunk_size(self, large_xml, logger):
        """Test splitting with custom chunk size."""
        breaker = XmlBreaker(xml=large_xml, logger=logger)
        chunks = breaker.split_records(breaker.root, number_of_records=100)
        
        assert len(chunks) == 5  # 500 records / 100 = 5 chunks

    def test_split_records_chunk_size_larger_than_records(self, simple_xml, logger):
        """Test when chunk size is larger than number of records."""
        breaker = XmlBreaker(xml=simple_xml, logger=logger)
        chunks = breaker.split_records(breaker.root, number_of_records=1000)
        
        assert len(chunks) == 1
        root = chunks[0].getroot()
        assert len(list(root)) == 3

    def test_split_records_preserves_element_tag(self, large_xml, logger):
        """Test that element tag is preserved in chunks."""
        breaker = XmlBreaker(xml=large_xml, logger=logger)
        chunks = breaker.split_records(breaker.root, number_of_records=100)
        
        for chunk in chunks:
            assert chunk.getroot().tag == "records"

    def test_split_records_preserves_attributes(self):
        """Test that element attributes are preserved."""
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<root attr1="value1" attr2="value2">
    <item>1</item>
    <item>2</item>
    <item>3</item>
</root>"""
        breaker = XmlBreaker(xml=xml, logger=logging.getLogger())
        chunks = breaker.split_records(breaker.root, number_of_records=2)
        
        for chunk in chunks:
            root = chunk.getroot()
            assert root.get("attr1") == "value1"
            assert root.get("attr2") == "value2"

    def test_split_records_with_none_element(self, xml_breaker):
        """Test splitting with None element raises ValueError."""
        with pytest.raises(ValueError, match="Element is required"):
            xml_breaker.split_records(None)

    def test_split_records_with_invalid_type(self, xml_breaker):
        """Test splitting with invalid type raises TypeError."""
        with pytest.raises(TypeError, match="must be an lxml Element"):
            xml_breaker.split_records("not an element")

    def test_split_records_display_messages(self, large_xml, logger, caplog):
        """Test that messages are displayed when flag is set."""
        breaker = XmlBreaker(xml=large_xml, logger=logger)
        
        with caplog.at_level(logging.INFO):
            breaker.split_records(breaker.root, number_of_records=100, display_messages=True)
        
        assert "500 records found" in caplog.text
        assert "100 records in chunk" in caplog.text

    def test_split_records_no_messages_by_default(self, large_xml, logger, caplog):
        """Test that no messages are displayed by default."""
        breaker = XmlBreaker(xml=large_xml, logger=logger)
        
        with caplog.at_level(logging.INFO):
            breaker.split_records(breaker.root, number_of_records=100)
        
        assert "records found" not in caplog.text

    def test_split_records_correct_counts(self, large_xml, logger):
        """Test that each chunk has correct number of records."""
        breaker = XmlBreaker(xml=large_xml, logger=logger)
        chunks = breaker.split_records(breaker.root, number_of_records=100)
        
        # First 4 chunks should have 100 records each
        for i in range(4):
            assert len(list(chunks[i].getroot())) == 100
        
        # Last chunk should have remaining records
        assert len(list(chunks[4].getroot())) == 100

    def test_split_records_with_one_record(self):
        """Test splitting element with single child."""
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<root>
    <item>Single Item</item>
</root>"""
        breaker = XmlBreaker(xml=xml, logger=logging.getLogger())
        chunks = breaker.split_records(breaker.root, number_of_records=10)
        
        assert len(chunks) == 1
        assert len(list(chunks[0].getroot())) == 1

    def test_split_records_preserves_text_content(self):
        """Test that text content is preserved."""
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<root>Text before
    <item>Item 1</item>
    <item>Item 2</item>
</root>"""
        breaker = XmlBreaker(xml=xml, logger=logging.getLogger())
        chunks = breaker.split_records(breaker.root, number_of_records=1)
        
        for chunk in chunks:
            root = chunk.getroot()
            assert root.text == "Text before\n    "

    @pytest.mark.parametrize("chunk_size,expected_chunks", [
        (1, 3),
        (2, 2),
        (3, 1),
        (5, 1),
    ])
    def test_split_records_various_chunk_sizes(self, simple_xml, logger, chunk_size, expected_chunks):
        """Test splitting with various chunk sizes."""
        breaker = XmlBreaker(xml=simple_xml, logger=logger)
        chunks = breaker.split_records(breaker.root, number_of_records=chunk_size)
        
        assert len(chunks) == expected_chunks


# Integration tests
class TestIntegration:
    """Integration tests combining multiple methods."""

    def test_full_workflow(self, large_xml, logger, tmp_path):
        """Test complete workflow: init, split, and write."""
        # Initialize
        breaker = XmlBreaker(xml=large_xml, logger=logger)
        
        # Split
        chunks = breaker.split_records(breaker.root, number_of_records=100)
        
        # Write each chunk
        for i, chunk in enumerate(chunks):
            output_file = tmp_path / f"chunk_{i}.xml"
            breaker.write_xml(chunk.getroot(), str(output_file))
            assert output_file.exists()
        
        # Verify all files created
        assert len(list(tmp_path.glob("*.xml"))) == 5

    def test_search_and_split(self, complex_xml, logger, tmp_path):
        """Test searching for element and then splitting it."""
        breaker = XmlBreaker(xml=complex_xml, logger=logger)
        
        # Find books element
        elements = list(breaker.root)
        books_element = breaker.get_element_by_tag("books", elements)
        
        assert books_element is not None
        
        # Split books
        chunks = breaker.split_records(books_element, number_of_records=2)
        
        assert len(chunks) == 2
        
        # Write chunks
        for i, chunk in enumerate(chunks):
            output_file = tmp_path / f"books_{i}.xml"
            breaker.write_xml(chunk.getroot(), str(output_file))
        
        # Verify
        assert (tmp_path / "books_0.xml").exists()
        assert (tmp_path / "books_1.xml").exists()

    def test_process_multiple_tags(self, complex_xml, logger, tmp_path):
        """Test processing multiple different tags."""
        breaker = XmlBreaker(xml=complex_xml, logger=logger)
        elements = list(breaker.root)
        
        for tag in ["books", "magazines"]:
            element = breaker.get_element_by_tag(tag, elements)
            if element is not None:
                chunks = breaker.split_records(element, number_of_records=10)
                for i, chunk in enumerate(chunks):
                    output_file = tmp_path / f"{tag}_{i}.xml"
                    breaker.write_xml(chunk.getroot(), str(output_file))
        
        # Verify files were created
        assert len(list[Any](tmp_path.glob("*.xml"))) > 0


# Additional edge cases and special scenarios
class TestEdgeCases:
    """Additional edge case tests."""

    def test_xml_with_namespaces(self, logger):
        """Test handling of XML with namespaces."""
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<root xmlns:custom="http://example.com/custom">
    <custom:item>1</custom:item>
    <custom:item>2</custom:item>
</root>"""
        breaker = XmlBreaker(xml=xml, logger=logger)
        assert breaker.root is not None
        assert len(list(breaker.root)) == 2

    def test_xml_with_cdata(self, logger):
        """Test handling of XML with CDATA sections."""
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<root>
    <item><![CDATA[This is <bold>CDATA</bold> content]]></item>
</root>"""
        breaker = XmlBreaker(xml=xml, logger=logger)
        assert breaker.root is not None
        item = list(breaker.root)[0]
        assert "CDATA" in item.text

    def test_xml_with_comments(self, logger):
        """Test handling of XML with comments."""
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<root>
    <!-- This is a comment -->
    <item>Content</item>
</root>"""
        breaker = XmlBreaker(xml=xml, logger=logger)
        assert breaker.root is not None
        # Comments are included in element children count with lxml
        assert len(list(breaker.root)) == 2

    def test_xml_with_processing_instructions(self, logger):
        """Test handling of XML with processing instructions."""
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<?target instruction?>
<root>
    <item>Content</item>
</root>"""
        breaker = XmlBreaker(xml=xml, logger=logger)
        assert breaker.root is not None
        assert breaker.root.tag == "root"

    def test_split_records_with_complex_attributes(self, logger):
        """Test splitting records with complex attributes."""
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<root xmlns:ns="http://example.com" attr="value">
    <item id="1" type="A" ns:special="x">Item 1</item>
    <item id="2" type="B" ns:special="y">Item 2</item>
    <item id="3" type="C" ns:special="z">Item 3</item>
</root>"""
        breaker = XmlBreaker(xml=xml, logger=logger)
        chunks = breaker.split_records(breaker.root, number_of_records=2)
        
        # Verify attributes are preserved
        for chunk in chunks:
            root = chunk.getroot()
            assert root.get("attr") == "value"

    def test_write_xml_with_special_characters(self, logger, tmp_path):
        """Test writing XML with special characters."""
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<root>
    <item>\xc3\xa9\xc3\xa0\xc3\xb9</item>
</root>"""
        breaker = XmlBreaker(xml=xml, logger=logger)
        output_file = tmp_path / "output.xml"
        breaker.write_xml(breaker.root, str(output_file))
        
        # Verify file exists and can be parsed
        tree = etree.parse(str(output_file))
        assert tree.getroot() is not None

    def test_split_records_preserves_order(self, logger):
        """Test that splitting preserves record order."""
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<root>
    <item>First</item>
    <item>Second</item>
    <item>Third</item>
    <item>Fourth</item>
    <item>Fifth</item>
</root>"""
        breaker = XmlBreaker(xml=xml, logger=logger)
        chunks = breaker.split_records(breaker.root, number_of_records=2)
        
        # Collect all items from chunks
        items = []
        for chunk in chunks:
            for child in chunk.getroot():
                items.append(child.text)
        
        assert items == ["First", "Second", "Third", "Fourth", "Fifth"]

    def test_get_element_by_tag_case_sensitive(self, logger):
        """Test that tag search is case-sensitive."""
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<root>
    <Item>1</Item>
    <item>2</item>
</root>"""
        breaker = XmlBreaker(xml=xml, logger=logger)
        elements = list(breaker.root)
        
        # Search for lowercase 'item' - should find second element
        result = breaker.get_element_by_tag("item", elements)
        assert result is not None
        assert result.text == "2"

    def test_write_xml_with_tail_text(self, logger, tmp_path):
        """Test writing element that has tail text."""
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<root>
    <item>1</item>
</root>"""
        breaker = XmlBreaker(xml=xml, logger=logger)
        item = list(breaker.root)[0]
        
        output_file = tmp_path / "output.xml"
        breaker.write_xml(item, str(output_file))
        
        # Verify file was written
        assert output_file.exists()
        tree = etree.parse(str(output_file))
        assert tree.getroot().tag == "item"

    def test_split_records_zero_chunk_size_edge_case(self, logger):
        """Test splitting with chunk size of 1."""
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<root>
    <item>1</item>
    <item>2</item>
</root>"""
        breaker = XmlBreaker(xml=xml, logger=logger)
        chunks = breaker.split_records(breaker.root, number_of_records=1)
        
        assert len(chunks) == 2
        assert len(list(chunks[0].getroot())) == 1
        assert len(list(chunks[1].getroot())) == 1

    def test_multiple_instances_independent(self, simple_xml, complex_xml, logger):
        """Test that multiple XmlBreaker instances are independent."""
        breaker1 = XmlBreaker(xml=simple_xml, logger=logger)
        breaker2 = XmlBreaker(xml=complex_xml, logger=logger)
        
        assert breaker1.root.tag == "root"
        assert breaker2.root.tag == "catalog"
        assert breaker1.root is not breaker2.root

    def test_write_xml_file_permissions(self, xml_breaker, tmp_path):
        """Test that written XML file is readable."""
        output_file = tmp_path / "output.xml"
        xml_breaker.write_xml(xml_breaker.root, str(output_file))
        
        # Verify file is readable
        assert output_file.stat().st_mode & 0o444 > 0

    def test_element_with_mixed_content(self, logger):
        """Test element with both text and child elements (mixed content)."""
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<root>Some text<item>Child</item>More text</root>"""
        breaker = XmlBreaker(xml=xml, logger=logger)
        chunks = breaker.split_records(breaker.root, number_of_records=10)
        
        assert len(chunks) == 1
        root = chunks[0].getroot()
        assert len(list(root)) == 1

    def test_deeply_nested_xml(self, logger):
        """Test handling of deeply nested XML structure."""
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<level1>
    <level2>
        <level3>
            <level4>
                <item>Deep content</item>
            </level4>
        </level3>
    </level2>
</level1>"""
        breaker = XmlBreaker(xml=xml, logger=logger)
        assert breaker.root.tag == "level1"
        
        # Navigate to deepest level
        level2 = list(breaker.root)[0]
        level3 = list(level2)[0]
        level4 = list(level3)[0]
        item = list(level4)[0]
        assert item.text == "Deep content"

    def test_empty_element(self, logger):
        """Test handling of empty elements."""
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<root>
    <empty/>
    <empty></empty>
    <item>Content</item>
</root>"""
        breaker = XmlBreaker(xml=xml, logger=logger)
        assert len(list(breaker.root)) == 3

    def test_get_element_by_tag_with_duplicates(self, logger):
        """Test get_element_by_tag returns first when multiple exist."""
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<root>
    <item priority="high">First</item>
    <item priority="low">Second</item>
    <item priority="medium">Third</item>
</root>"""
        breaker = XmlBreaker(xml=xml, logger=logger)
        elements = list(breaker.root)
        
        result = breaker.get_element_by_tag("item", elements)
        assert result is not None
        assert result.text == "First"
        assert result.get("priority") == "high"

    def test_split_records_maintains_element_properties(self, logger):
        """Test that split maintains all element properties."""
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<records version="1.0" timestamp="2024-01-01">
    <record>1</record>
    <record>2</record>
    <record>3</record>
</records>"""
        breaker = XmlBreaker(xml=xml, logger=logger)
        chunks = breaker.split_records(breaker.root, number_of_records=1)
        
        for chunk in chunks:
            root = chunk.getroot()
            assert root.get("version") == "1.0"
            assert root.get("timestamp") == "2024-01-01"