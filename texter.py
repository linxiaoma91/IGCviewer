import cv2
import numpy as np

class TextPlacementGrid:
    def __init__(self, img_width, img_height, grid_rows=10, grid_cols=10):
        self.img_width = img_width
        self.img_height = img_height
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols
        self.cell_width = img_width / grid_cols  # Float for precise shifts
        self.cell_height = img_height / grid_rows
        self.grid = np.zeros((grid_rows, grid_cols), dtype=bool)  # False = free, True = occupied

    def get_grid_cell(self, x, y):
        """Convert image (x,y) to grid (row, col)."""
        col = int(x / self.cell_width)
        row = int(y / self.cell_height)
        # Clamp to grid bounds
        row = max(0, min(row, self.grid_rows - 1))
        col = max(0, min(col, self.grid_cols - 1))
        return (row, col)

    def is_cell_free(self, row, col):
        """Check if the target cell is free (ignoring neighbors)."""
        return not self.grid[row, col]

    def mark_cell_occupied(self, row, col):
        """Mark target cell + 8 neighbors as occupied (enforce 1-cell spacing)."""
        for r in range(max(0, row - 1), min(self.grid_rows, row + 2)):
            for c in range(max(0, col - 1), min(self.grid_cols, col + 2)):
                self.grid[r, c] = True

    def find_free_cell_near(self, desired_row, desired_col):
        """Spiral search for nearest free cell (no 3x3 zone check)."""
        if self.is_cell_free(desired_row, desired_col):
            return (desired_row, desired_col)

        # Spiral search pattern
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # Right, Down, Left, Up
        step_size = 1
        steps_taken = 0
        direction_idx = 0
        current_row, current_col = desired_row, desired_col

        while True:
            for _ in range(step_size):
                current_row += directions[direction_idx][0]
                current_col += directions[direction_idx][1]

                # Check grid bounds and cell availability
                if (0 <= current_row < self.grid_rows and
                        0 <= current_col < self.grid_cols):
                    if self.is_cell_free(current_row, current_col):
                        return (current_row, current_col)

            direction_idx = (direction_idx + 1) % 4
            steps_taken += 1
            if steps_taken % 2 == 0:
                step_size += 1

            # Prevent infinite loop if grid is full
            if step_size > max(self.grid_rows, self.grid_cols):
                return None

    def place_text(self, img, text, x, y, font_scale=0.5,
                   color=(0, 0, 0), thickness=1, font=cv2.FONT_HERSHEY_SIMPLEX):
        """Place text at (x,y), shifting if the target cell is occupied."""
        desired_row, desired_col = self.get_grid_cell(x, y)
        free_row, free_col = self.find_free_cell_near(desired_row, desired_col)

        if free_row is None:
            print("No free space found!")
            return img

        # Calculate shift
        row_offset = free_row - desired_row
        col_offset = free_col - desired_col
        shifted_x = x + col_offset * self.cell_width
        shifted_y = y + row_offset * self.cell_height

        # Mark target + neighbors as occupied (enforce 1-cell spacing)
        self.mark_cell_occupied(free_row, free_col)

        # Adjust y for text baseline and draw
        (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        shifted_y += text_height + baseline
        cv2.putText(img, text, (int(shifted_x), int(shifted_y)), font, font_scale, color, thickness, cv2.LINE_AA)
        return img


import cv2
import numpy as np
import math
from collections import defaultdict


class TextLabelManager:
    def __init__(self, repulsion_radius=100, attraction_force=0.1, repulsion_force=0.1, damping=1):
        self.labels = {}  # object_id: {'pos': (x,y), 'text_pos': (x,y), 'velocity': (vx,vy)}
        self.repulsion_radius = repulsion_radius
        self.attraction_force = attraction_force
        self.repulsion_force = repulsion_force
        self.damping = damping

    def update_label_positions(self):
        # Calculate forces
        forces = defaultdict(lambda: np.array([0.0, 0.0]))

        # Attraction forces between objects and their labels
        for obj_id, data in self.labels.items():
            obj_pos = np.array(data['pos'])
            text_pos = np.array(data['text_pos'])

            # Attraction force (text wants to stay near object)
            direction = obj_pos - text_pos
            distance = np.linalg.norm(direction)
            if distance > 0:
                direction = direction / distance
                force = direction * min(self.attraction_force * distance, 10)
                forces[obj_id] += force

        # Repulsion forces between all labels
        label_ids = list(self.labels.keys())
        for i, id1 in enumerate(label_ids):
            for id2 in label_ids[i + 1:]:
                pos1 = np.array(self.labels[id1]['text_pos'])
                pos2 = np.array(self.labels[id2]['text_pos'])

                direction = pos1 - pos2
                distance = np.linalg.norm(direction)

                if distance < self.repulsion_radius:
                    if distance < 10:  # Avoid division by zero
                        direction = np.random.rand(2) - 0.5
                        distance = 10

                    direction = direction / distance
                    # Stronger repulsion when closer
                    force = direction * (self.repulsion_force * (self.repulsion_radius - distance))
                    forces[id1] += force
                    forces[id2] -= force

        # Update positions with damping for smoothness
        for obj_id, data in self.labels.items():
            # Update velocity
            data['velocity'] = data['velocity'] * self.damping + forces[obj_id]

            # Update position
            new_pos = np.array(data['text_pos']) + data['velocity']
            data['text_pos'] = tuple(new_pos.astype(int))

            # Optional: Keep text within screen bounds
            #data['text_pos'] = (
            #    max(0, min(data['text_pos'][0], screen_width - 100)),
            #    max(0, min(data['text_pos'][1], screen_height - 20))
            #)

    def add_or_update_object(self, obj_id, position, text):
        if obj_id not in self.labels:
            # Start with text to the right of the object
            self.labels[obj_id] = {
                'pos': position,
                'text_pos': (position[0] + 20, position[1]),
                'velocity': np.array([0.0, 0.0]),
                'text': text
            }
        else:
            # Update object position
            self.labels[obj_id]['pos'] = position

    def draw_labels(self, frame):
        self.update_label_positions()

        for obj_id, data in self.labels.items():
            # Draw line from object to text
            cv2.line(frame, data['pos'], (data['text_pos'][0], data['text_pos'][1]-10), (64, 64, 64), 1)

            # Draw text with background for readability
            text_size = cv2.getTextSize(data['text'], cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            text_x, text_y = data['text_pos']

            #Text background
            cv2.rectangle(frame,
                          (text_x - 2, text_y - text_size[1] - 12),
                          (text_x + text_size[0] + 2, text_y - 8),
                          (0, 0, 0), -1)

            # Text itself
            cv2.putText(frame, data['text'], (text_x, text_y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)




# Example Usage
if __name__ == "__main__":
    # Create a blank white image
    img = 255 * np.ones((500, 800, 3), dtype=np.uint8)

    # Initialize the grid
    grid = TextPlacementGrid(img.shape[1], img.shape[0], grid_rows=10, grid_cols=10)

    # Texts clustered near (400, 250) and (200, 100)
    texts_and_positions = [
        ("Hello", 400, 250),  # Placed exactly
        ("World", 400, 250),  # Shifted 1 cell away
        ("OpenCV", 400, 250),  # Shifted another cell away
        ("Text", 200, 100),
        ("Placement", 200, 100),
    ]

    # Place all texts
    for text, x, y in texts_and_positions:
        img = grid.place_text(img, text, x, y)

    # Display the result
    cv2.imshow("Text Placement (1-Cell Minimum Spacing)", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()