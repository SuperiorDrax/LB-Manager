import re

class DataParser:
    @staticmethod
    def parse_text(text):
        # Initialize fields
        author = ""
        title = ""
        group = ""
        show = ""
        magazine = ""
        origin = ""
        websign = ""
        tag = ""
        read_status = "unread"
        progress = 0
        
        # Extract websign from the beginning (1-7 digit integer)
        websign_match = re.match(r'^(\d{1,7})\s*(.*)', text)
        if websign_match:
            websign = websign_match.group(1)
            text = websign_match.group(2).strip()
        else:
            # If no websign found at beginning, return None to indicate error
            return None
        
        # Extract show info (content in parentheses at the beginning, after websign)
        show_match = re.match(r'\(([^)]+)\)\s*(.*)', text)
        if show_match:
            show = show_match.group(1)
            text = show_match.group(2).strip()
        
        # Extract author info (content in square brackets)
        author_match = re.match(r'\[([^]]+)\](.*)', text)
        if author_match:
            author_info = author_match.group(1)
            remaining_text = author_match.group(2).strip()
            
            # Check if author_info contains parentheses at the end
            group_match = re.search(r'\(([^)]+)\)$', author_info)
            if group_match:
                # Format: [group (author)] - group before parentheses, author inside parentheses
                author = group_match.group(1)
                group = author_info[:group_match.start()].strip()
            else:
                # Format: [author] - no parentheses, entire content is author
                author = author_info
                group = ""
            
            # The remaining text is title plus possible origin/magazine
            text = remaining_text
        else:
            # No author info found, return None to indicate error
            return None
        
        # Extract origin/magazine (content in parentheses at the end of title)
        origin_match = re.search(r'\(([^)]+)\)$', text)
        if origin_match:
            origin_info = origin_match.group(1)
            title_text = text[:origin_match.start()].strip()
            
            # Check if origin_info contains keywords for magazine
            origin_info_upper = origin_info.upper()
            if any(keyword in origin_info_upper for keyword in ['COMIC', 'VOL', '月号', 'コミック', 'WEEKLY', '永遠娘']):
                magazine = origin_info
            else:
                origin = origin_info
            
            title = title_text
        else:
            # No origin/magazine info, the entire remaining text is title
            title = text.strip()
        
        # Check if required fields are present
        if not websign or not author or not title:
            return None
        
        return author, title, group, show, magazine, origin, websign, tag, read_status, progress