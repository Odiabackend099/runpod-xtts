"""
Unit tests for SSML parser
"""

import pytest
from src.utils.ssml_parser import SSMLParser


class TestSSMLParser:
    """Test cases for SSML parser"""
    
    @pytest.fixture
    def parser(self):
        """Create SSML parser instance"""
        return SSMLParser()
    
    def test_parse_simple_text(self, parser):
        """Test parsing simple text without SSML"""
        text = "Hello world"
        result = parser.parse(text)
        assert result == "Hello world"
    
    def test_parse_speak_tag(self, parser):
        """Test parsing speak tag"""
        ssml = "<speak>Hello world</speak>"
        result = parser.parse(ssml)
        assert result == "Hello world"
    
    def test_parse_break_tag(self, parser):
        """Test parsing break tag"""
        ssml = "<speak>Hello<break time='0.5s'/>world</speak>"
        result = parser.parse(ssml)
        assert "Hello" in result
        assert "world" in result
        # Should have some spacing for the break
        assert len(result.split()) >= 2
    
    def test_parse_break_different_times(self, parser):
        """Test parsing break tags with different time values"""
        # Short break
        ssml1 = "<speak>Hello<break time='0.1s'/>world</speak>"
        result1 = parser.parse(ssml1)
        
        # Long break
        ssml2 = "<speak>Hello<break time='2s'/>world</speak>"
        result2 = parser.parse(ssml2)
        
        # Long break should have more spacing
        assert len(result2) > len(result1)
    
    def test_parse_prosody_rate(self, parser):
        """Test parsing prosody with rate"""
        ssml = "<speak><prosody rate='slow'>Hello world</prosody></speak>"
        result = parser.parse(ssml)
        assert "Hello" in result
        assert "world" in result
        # Slow rate should add extra spaces
        assert "  " in result
    
    def test_parse_prosody_fast(self, parser):
        """Test parsing prosody with fast rate"""
        ssml = "<speak><prosody rate='fast'>Hello   world</prosody></speak>"
        result = parser.parse(ssml)
        # Fast rate should normalize spaces
        assert "   " not in result
    
    def test_parse_prosody_pitch(self, parser):
        """Test parsing prosody with pitch"""
        ssml = "<speak><prosody pitch='high'>Hello</prosody></speak>"
        result = parser.parse(ssml)
        assert "*Hello*" in result
    
    def test_parse_prosody_low_pitch(self, parser):
        """Test parsing prosody with low pitch"""
        ssml = "<speak><prosody pitch='low'>Hello</prosody></speak>"
        result = parser.parse(ssml)
        assert "_Hello_" in result
    
    def test_parse_prosody_volume(self, parser):
        """Test parsing prosody with volume"""
        ssml = "<speak><prosody volume='loud'>Hello</prosody></speak>"
        result = parser.parse(ssml)
        assert "**Hello**" in result
    
    def test_parse_emphasis_strong(self, parser):
        """Test parsing emphasis with strong level"""
        ssml = "<speak><emphasis level='strong'>Hello</emphasis></speak>"
        result = parser.parse(ssml)
        assert "**Hello**" in result
    
    def test_parse_emphasis_moderate(self, parser):
        """Test parsing emphasis with moderate level"""
        ssml = "<speak><emphasis level='moderate'>Hello</emphasis></speak>"
        result = parser.parse(ssml)
        assert "*Hello*" in result
    
    def test_parse_say_as_characters(self, parser):
        """Test parsing say-as with characters"""
        ssml = "<speak><say-as interpret-as='characters'>ABC</say-as></speak>"
        result = parser.parse(ssml)
        assert "A B C" in result
    
    def test_parse_say_as_digits(self, parser):
        """Test parsing say-as with digits"""
        ssml = "<speak><say-as interpret-as='digits'>123</say-as></speak>"
        result = parser.parse(ssml)
        assert "1 2 3" in result
    
    def test_parse_say_as_number(self, parser):
        """Test parsing say-as with number"""
        ssml = "<speak><say-as interpret-as='number'>5</say-as></speak>"
        result = parser.parse(ssml)
        assert "five" in result
    
    def test_parse_sub_alias(self, parser):
        """Test parsing sub with alias"""
        ssml = "<speak><sub alias='world'>earth</sub></speak>"
        result = parser.parse(ssml)
        assert "world" in result
        assert "earth" not in result
    
    def test_parse_audio_tag(self, parser):
        """Test parsing audio tag"""
        ssml = "<speak><audio src='sound.wav'>fallback</audio></speak>"
        result = parser.parse(ssml)
        assert "[Audio: sound.wav]" in result
    
    def test_parse_complex_ssml(self, parser):
        """Test parsing complex SSML with multiple tags"""
        ssml = """
        <speak>
            <prosody rate='slow'>Hello</prosody>
            <break time='0.5s'/>
            <emphasis level='strong'>world</emphasis>
            <break time='1s'/>
            <say-as interpret-as='characters'>TTS</say-as>
        </speak>
        """
        result = parser.parse(ssml)
        
        # Should contain all the text elements
        assert "Hello" in result
        assert "**world**" in result
        assert "T T S" in result
    
    def test_parse_invalid_xml(self, parser):
        """Test parsing invalid XML"""
        invalid_ssml = "<speak>Hello<unclosed>world</speak>"
        result = parser.parse(invalid_ssml)
        # Should fallback to text extraction
        assert "Hello" in result
        assert "world" in result
    
    def test_parse_unsupported_tag(self, parser):
        """Test parsing unsupported tag"""
        ssml = "<speak><unsupported>Hello</unsupported></speak>"
        result = parser.parse(ssml)
        assert "Hello" in result
    
    def test_clean_ssml_adds_speak_tag(self, parser):
        """Test that clean_ssml adds speak tag if missing"""
        text = "Hello world"
        cleaned = parser._clean_ssml(text)
        assert cleaned.startswith("<speak>")
        assert cleaned.endswith("</speak>")
    
    def test_clean_ssml_removes_xml_declaration(self, parser):
        """Test that clean_ssml removes XML declaration"""
        ssml = "<?xml version='1.0'?><speak>Hello</speak>"
        cleaned = parser._clean_ssml(ssml)
        assert "<?xml" not in cleaned
        assert "<speak>Hello</speak>" in cleaned
    
    def test_number_to_words(self, parser):
        """Test number to words conversion"""
        assert parser._number_to_words("0") == "zero"
        assert parser._number_to_words("5") == "five"
        assert parser._number_to_words("15") == "fifteen"
        assert parser._number_to_words("25") == "twenty five"
    
    def test_extract_text_only(self, parser):
        """Test extracting text from markup"""
        text = "<tag>Hello</tag> <another>world</another>"
        result = parser._extract_text_only(text)
        assert result == "Hello world"
    
    def test_validate_ssml_valid(self, parser):
        """Test SSML validation with valid input"""
        ssml = "<speak><break time='0.5s'/>Hello</speak>"
        result = parser.validate_ssml(ssml)
        
        assert result["valid"] is True
        assert result["unsupported_tags"] == []
        assert "Hello" in result["parsed_text"]
    
    def test_validate_ssml_invalid(self, parser):
        """Test SSML validation with invalid input"""
        ssml = "<speak><unclosed>Hello</speak>"
        result = parser.validate_ssml(ssml)
        
        assert result["valid"] is False
        assert "error" in result
        assert "Hello" in result["parsed_text"]
    
    def test_validate_ssml_unsupported_tags(self, parser):
        """Test SSML validation with unsupported tags"""
        ssml = "<speak><unsupported>Hello</unsupported></speak>"
        result = parser.validate_ssml(ssml)
        
        assert result["valid"] is True
        assert "unsupported" in result["unsupported_tags"]
