"""
SSML Parser for Enhanced Text Processing
Supports prosody, pauses, emphasis, and other SSML features
"""

import re
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class SSMLParser:
    """Parse SSML markup and convert to enhanced text"""
    
    def __init__(self):
        self.supported_tags = {
            'speak': self._handle_speak,
            'break': self._handle_break,
            'prosody': self._handle_prosody,
            'emphasis': self._handle_emphasis,
            'say-as': self._handle_say_as,
            'sub': self._handle_sub,
            'audio': self._handle_audio
        }
    
    def parse(self, ssml_text: str) -> str:
        """
        Parse SSML text and return enhanced text for TTS
        
        Args:
            ssml_text: SSML markup text
            
        Returns:
            Enhanced text with SSML features applied
        """
        try:
            # Clean and validate SSML
            ssml_text = self._clean_ssml(ssml_text)
            
            # Parse XML
            root = ET.fromstring(ssml_text)
            
            # Process the SSML
            result = self._process_element(root)
            
            return result.strip()
            
        except ET.ParseError as e:
            logger.warning(f"Invalid SSML, treating as plain text: {e}")
            return self._extract_text_only(ssml_text)
        except Exception as e:
            logger.error(f"Error parsing SSML: {e}")
            return self._extract_text_only(ssml_text)
    
    def _clean_ssml(self, ssml_text: str) -> str:
        """Clean and normalize SSML text"""
        # Ensure proper XML structure
        if not ssml_text.strip().startswith('<'):
            ssml_text = f'<speak>{ssml_text}</speak>'
        
        # Remove XML declaration if present
        ssml_text = re.sub(r'<\?xml[^>]*\?>', '', ssml_text)
        
        return ssml_text.strip()
    
    def _process_element(self, element: ET.Element) -> str:
        """Process an XML element and its children"""
        tag_name = element.tag.lower()
        
        if tag_name in self.supported_tags:
            return self.supported_tags[tag_name](element)
        else:
            # Unknown tag, just process children
            return self._process_children(element)
    
    def _process_children(self, element: ET.Element) -> str:
        """Process all child elements and text"""
        result = ""
        
        if element.text:
            result += element.text
        
        for child in element:
            result += self._process_element(child)
            if child.tail:
                result += child.tail
        
        return result
    
    def _handle_speak(self, element: ET.Element) -> str:
        """Handle <speak> tag"""
        return self._process_children(element)
    
    def _handle_break(self, element: ET.Element) -> str:
        """Handle <break> tag for pauses"""
        time_attr = element.get('time', '0.5s')
        
        # Convert time to pause duration
        if time_attr.endswith('s'):
            duration = float(time_attr[:-1])
        elif time_attr.endswith('ms'):
            duration = float(time_attr[:-2]) / 1000
        else:
            duration = 0.5
        
        # Add pause based on duration
        if duration <= 0.2:
            return " "  # Short pause
        elif duration <= 0.5:
            return "  "  # Medium pause
        elif duration <= 1.0:
            return "   "  # Long pause
        else:
            return "    "  # Very long pause
    
    def _handle_prosody(self, element: ET.Element) -> str:
        """Handle <prosody> tag for speech rate and pitch"""
        rate = element.get('rate', 'medium')
        pitch = element.get('pitch', 'medium')
        volume = element.get('volume', 'medium')
        
        text = self._process_children(element)
        
        # Apply prosody modifications
        if rate == 'slow':
            # Add slight pauses between words
            text = text.replace(' ', '  ')
        elif rate == 'fast':
            # Remove extra spaces
            text = re.sub(r'\s+', ' ', text)
        
        if pitch == 'high':
            # Add emphasis markers
            text = f"*{text}*"
        elif pitch == 'low':
            # Add low pitch markers
            text = f"_{text}_"
        
        if volume == 'loud':
            text = f"**{text}**"
        elif volume == 'soft':
            text = f"__{text}__"
        
        return text
    
    def _handle_emphasis(self, element: ET.Element) -> str:
        """Handle <emphasis> tag"""
        level = element.get('level', 'moderate')
        text = self._process_children(element)
        
        if level == 'strong':
            return f"**{text}**"
        elif level == 'moderate':
            return f"*{text}*"
        else:
            return text
    
    def _handle_say_as(self, element: ET.Element) -> str:
        """Handle <say-as> tag for special pronunciation"""
        interpret_as = element.get('interpret-as', 'characters')
        text = self._process_children(element)
        
        if interpret_as == 'characters':
            # Spell out characters
            return ' '.join(text)
        elif interpret_as == 'digits':
            # Say each digit separately
            return ' '.join(text)
        elif interpret_as == 'number':
            # Convert to spoken number
            return self._number_to_words(text)
        else:
            return text
    
    def _handle_sub(self, element: ET.Element) -> str:
        """Handle <sub> tag for substitutions"""
        alias = element.get('alias')
        if alias:
            return alias
        return self._process_children(element)
    
    def _handle_audio(self, element: ET.Element) -> str:
        """Handle <audio> tag (not supported, return fallback)"""
        src = element.get('src', '')
        return f"[Audio: {src}]"
    
    def _number_to_words(self, number_str: str) -> str:
        """Convert number string to words"""
        try:
            number = float(number_str)
            if number.is_integer():
                return self._int_to_words(int(number))
            else:
                return str(number)  # Fallback for decimals
        except ValueError:
            return number_str
    
    def _int_to_words(self, num: int) -> str:
        """Convert integer to words"""
        if num == 0:
            return "zero"
        elif num < 20:
            return ["", "one", "two", "three", "four", "five", "six", "seven", 
                   "eight", "nine", "ten", "eleven", "twelve", "thirteen", 
                   "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", 
                   "nineteen"][num]
        elif num < 100:
            tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", 
                   "seventy", "eighty", "ninety"][num // 10]
            ones = num % 10
            return tens + (" " + self._int_to_words(ones) if ones else "")
        else:
            return str(num)  # Fallback for large numbers
    
    def _extract_text_only(self, text: str) -> str:
        """Extract plain text from SSML-like markup"""
        # Remove all XML-like tags
        text = re.sub(r'<[^>]+>', '', text)
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def validate_ssml(self, ssml_text: str) -> Dict[str, Any]:
        """Validate SSML syntax and return validation results"""
        try:
            # Clean SSML
            cleaned_ssml = self._clean_ssml(ssml_text)
            
            # Parse XML
            root = ET.fromstring(cleaned_ssml)
            
            # Check for unsupported tags
            unsupported_tags = []
            for elem in root.iter():
                if elem.tag.lower() not in self.supported_tags:
                    unsupported_tags.append(elem.tag)
            
            return {
                "valid": True,
                "unsupported_tags": list(set(unsupported_tags)),
                "parsed_text": self.parse(ssml_text)
            }
            
        except ET.ParseError as e:
            return {
                "valid": False,
                "error": f"XML parsing error: {e}",
                "parsed_text": self._extract_text_only(ssml_text)
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Validation error: {e}",
                "parsed_text": self._extract_text_only(ssml_text)
            }
