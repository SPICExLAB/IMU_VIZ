"""Dynamic device grid layout manager"""

class DeviceGridLayout:
    """Manages dynamic grid layout for device panels"""
    
    def __init__(self, box_size=200, margin=20, max_per_row=2):
        self.box_size = box_size
        self.margin = margin
        self.max_per_row = max_per_row
        self.device_order = ['phone', 'headphone', 'watch']
        
        # Starting position for device grid
        self.start_x = 30
        self.start_y = 200  # Below the reference section
        
        # Panel width constraint
        self.panel_width = 480  # Approximate left panel width
    
    def calculate_positions(self, active_devices):
        """Calculate device positions based on connected devices"""
        positions = {}
        
        # Separate active and inactive devices
        inactive_devices = [d for d in self.device_order if d not in active_devices]
        
        if len(active_devices) == 0:
            # All inactive - show as small boxes in a row
            small_size = 80
            small_margin = 15
            total_width = len(self.device_order) * small_size + (len(self.device_order) - 1) * small_margin
            start_x = (self.panel_width - total_width) // 2
            
            for i, device in enumerate(self.device_order):
                x = start_x + i * (small_size + small_margin)
                y = self.start_y + 50  # Center vertically
                
                positions[device] = {
                    'center': (x + small_size // 2, y + small_size // 2),
                    'bounds': (x, y, small_size, small_size),
                    'size': small_size,
                    'active': False
                }
        
        elif len(active_devices) == 1:
            # One active - large box, two small boxes below
            active_device = active_devices[0]
            
            # Active device - large centered box
            large_size = 220
            x = (self.panel_width - large_size) // 2
            y = self.start_y
            
            positions[active_device] = {
                'center': (x + large_size // 2, y + large_size // 2),
                'bounds': (x, y, large_size, large_size),
                'size': large_size,
                'active': True
            }
            
            # Inactive devices - small boxes below
            small_size = 80
            small_margin = 15
            inactive_y = y + large_size + 30
            
            # Center the two small boxes
            total_width = len(inactive_devices) * small_size + (len(inactive_devices) - 1) * small_margin
            start_x = (self.panel_width - total_width) // 2
            
            for i, device in enumerate(inactive_devices):
                x = start_x + i * (small_size + small_margin)
                
                positions[device] = {
                    'center': (x + small_size // 2, inactive_y + small_size // 2),
                    'bounds': (x, inactive_y, small_size, small_size),
                    'size': small_size,
                    'active': False
                }
        
        elif len(active_devices) == 2:
            # Two active - side by side, one small below
            # Use more of the available width
            box_size = 200
            total_active_width = 2 * box_size + self.margin
            start_x = (self.panel_width - total_active_width) // 2
            
            for i, device in enumerate(active_devices):
                x = start_x + i * (box_size + self.margin)
                y = self.start_y
                
                positions[device] = {
                    'center': (x + box_size // 2, y + box_size // 2),
                    'bounds': (x, y, box_size, box_size),
                    'size': box_size,
                    'active': True
                }
            
            # Inactive device - small box below, centered
            if inactive_devices:
                small_size = 80
                inactive_y = self.start_y + box_size + 30
                x = (self.panel_width - small_size) // 2
                
                positions[inactive_devices[0]] = {
                    'center': (x + small_size // 2, inactive_y + small_size // 2),
                    'bounds': (x, inactive_y, small_size, small_size),
                    'size': small_size,
                    'active': False
                }
        
        else:
            # All active - 2x2 grid
            box_size = 180
            col_width = box_size + self.margin
            row_height = box_size + self.margin
            
            # Center the grid
            grid_width = 2 * box_size + self.margin
            start_x = (self.panel_width - grid_width) // 2
            
            for i, device in enumerate(active_devices[:4]):  # Max 4 devices
                row = i // 2
                col = i % 2
                
                x = start_x + col * col_width
                y = self.start_y + row * row_height
                
                positions[device] = {
                    'center': (x + box_size // 2, y + box_size // 2),
                    'bounds': (x, y, box_size, box_size),
                    'size': box_size,
                    'active': True
                }
        
        return positions
    
    def get_panel_height(self, num_devices):
        """Calculate total height needed for all device panels"""
        rows = (num_devices + self.max_per_row - 1) // self.max_per_row
        return self.start_y + rows * (self.box_size + self.margin) + self.margin