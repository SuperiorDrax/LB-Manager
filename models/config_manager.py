import configparser
import os

class ConfigManager:
    def __init__(self, config_file="config.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.load_config()
    
    def load_config(self):
        """Load configuration from file or create default"""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file, encoding='utf-8')
        else:
            self.create_default_config()
    
    def create_default_config(self):
        """Create default configuration file"""
        self.config['WebSettings'] = {
            'jm_website': 'baidu.com',
            'dist_website': 'example.com'
        }
        self.config['LibSettings'] = {
            'lib_path': ''
        }
        self.config['ViewSettings'] = {  # New section
            'slide_speed': '1.0'
        }
        self.config['WindowSettings'] = {'geometry': '', 'state': ''}
        self.save_config()
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get_jm_website(self):
        """Get JM website setting"""
        try:
            return self.config.get('WebSettings', 'jm_website', fallback='baidu.com')
        except:
            return 'baidu.com'
    
    def set_jm_website(self, website):
        """Set JM website setting"""
        if not self.config.has_section('WebSettings'):
            self.config.add_section('WebSettings')
        self.config.set('WebSettings', 'jm_website', website)
        self.save_config()
    
    def get_dist_website(self):
        """Get Dist website setting"""
        try:
            return self.config.get('WebSettings', 'dist_website', fallback='example.com')
        except:
            return 'example.com'
    
    def set_dist_website(self, website):
        """Set Dist website setting"""
        if not self.config.has_section('WebSettings'):
            self.config.add_section('WebSettings')
        self.config.set('WebSettings', 'dist_website', website)
        self.save_config()
    
    def get_lib_path(self):
        """Get library path setting"""
        try:
            return self.config.get('LibSettings', 'lib_path', fallback='')
        except:
            return ''
    
    def set_lib_path(self, lib_path):
        """Set library path setting"""
        if not self.config.has_section('LibSettings'):
            self.config.add_section('LibSettings')
        self.config.set('LibSettings', 'lib_path', lib_path)
        self.save_config()
    
    def get_slide_speed(self):
        """Get slide show speed setting"""
        try:
            speed_str = self.config.get('ViewSettings', 'slide_speed', fallback='1.0')
            return float(speed_str)  # Convert string to float
        except (ValueError, TypeError):
            return 1.0  # Default value if conversion fails

    def set_slide_speed(self, speed):
        """Set slide show speed setting"""
        if not self.config.has_section('ViewSettings'):
            self.config.add_section('ViewSettings')
        # Ensure speed is converted to string before saving
        self.config.set('ViewSettings', 'slide_speed', str(float(speed)))
        self.save_config()
    
    def get_window_state(self):
        """Get window state configuration"""
        try:
            geometry = self.config.get('WindowState', 'geometry', fallback='')
            maximized = self.config.getboolean('WindowState', 'maximized', fallback=False)
            table_geometry = self.config.get('WindowState', 'table_geometry', fallback='')
            
            # Return empty strings for first run detection
            return {
                'geometry': geometry,
                'maximized': maximized,
                'table_geometry': table_geometry
            }
        except:
            return {'geometry': '', 'maximized': False, 'table_geometry': ''}

    def set_window_state(self, geometry, maximized, table_geometry):
        """Set window state configuration"""
        if not self.config.has_section('WindowState'):
            self.config.add_section('WindowState')
        self.config.set('WindowState', 'geometry', geometry)
        self.config.set('WindowState', 'maximized', str(maximized).lower())
        self.config.set('WindowState', 'table_geometry', table_geometry)
        self.save_config()
        
    def get_column_config(self):
        """Get column configuration"""
        try:
            visible = self.config.get('ColumnConfig', 'visible', fallback='1,1,1,1,1,1,1,1')
            order = self.config.get('ColumnConfig', 'order', fallback='0,1,2,3,4,5,6,7')
            return {
                'visible': [x == '1' for x in visible.split(',')],
                'order': [int(x) for x in order.split(',')]
            }
        except:
            return {
                'visible': [True, True, True, True, True, True, True, True],
                'order': [0, 1, 2, 3, 4, 5, 6, 7]
            }

    def set_column_config(self, visible, order):
        """Set column configuration"""
        if not self.config.has_section('ColumnConfig'):
            self.config.add_section('ColumnConfig')
        visible_str = ','.join(['1' if v else '0' for v in visible])
        order_str = ','.join([str(x) for x in order])
        self.config.set('ColumnConfig', 'visible', visible_str)
        self.config.set('ColumnConfig', 'order', order_str)
        self.save_config()

    def get_duplicate_check(self):
        """Get duplicate check setting"""
        try:
            return self.config.getboolean('Validation', 'duplicate_check', fallback=True)
        except:
            return True

    def set_duplicate_check(self, enabled):
        """Set duplicate check setting"""
        if not self.config.has_section('Validation'):
            self.config.add_section('Validation')
        self.config.set('Validation', 'duplicate_check', str(enabled))
        self.save_config()