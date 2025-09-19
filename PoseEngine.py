import cv2
import mediapipe as mp
import numpy as np

# --- 颜色和字体常量 ---
GREEN, RED, BLUE, WHITE, BLACK = (0, 255, 0), (0, 0, 255), (255, 0, 0), (255, 255, 255), (0, 0, 0)
YELLOW = (0, 255, 255)
FONT = cv2.FONT_HERSHEY_SIMPLEX

# --- 强大的箭头绘制函数 (全局) ---
def draw_arrow(image, start_point, end_point, text=None):
    """绘制一个更醒目的、带描边和文字的箭头"""
    cv2.arrowedLine(image, start_point, end_point, BLACK, 12, tipLength=0.4)
    cv2.arrowedLine(image, start_point, end_point, YELLOW, 8, tipLength=0.4)
    if text:
        text_pos = (start_point[0] - 80, start_point[1] - 20)
        cv2.putText(image, text, (text_pos[0]+2, text_pos[1]+2), FONT, 0.9, BLACK, 2, cv2.LINE_AA)
        cv2.putText(image, text, text_pos, FONT, 0.9, WHITE, 2, cv2.LINE_AA)

class PoseEngine:
    def __init__(self, mode='squat'):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7)
        self.mp_drawing = mp.solutions.drawing_utils
        self.BODY_PARTS = {
            'torso': [(11, 12), (11, 23), (12, 24), (23, 24)], 'left_arm': [(11, 13), (13, 15)],
            'right_arm': [(12, 14), (14, 16)], 'left_leg': [(23, 25), (25, 27)], 'right_leg': [(24, 26), (26, 28)]
        }
        self.show_skeleton = True
        self.set_mode(mode)

    def set_mode(self, mode):
        self.exercise_mode = mode
        self.rep_counter = 0
        self.feedback_dict = {'text': [], 'arrows': [], 'faulty_parts': set()}
        self.current_stage = 'up' if mode == 'squat' else 'down'

    def toggle_skeleton(self):
        self.show_skeleton = not self.show_skeleton
        return self.show_skeleton

    def calculate_angle(self, a, b, c):
        a, b, c = np.array(a), np.array(b), np.array(c)
        radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
        angle = np.abs(radians * 180.0 / np.pi)
        return 360 - angle if angle > 180.0 else angle

    def _handle_squat(self, landmarks):
        feedback = {'text': [], 'arrows': [], 'faulty_parts': set()}
        coords = self.mp_pose.PoseLandmark
        
        # --- FIX START ---
        hip_l = [landmarks[coords.LEFT_HIP.value].x, landmarks[coords.LEFT_HIP.value].y]
        knee_l = [landmarks[coords.LEFT_KNEE.value].x, landmarks[coords.LEFT_KNEE.value].y]
        ankle_l = [landmarks[coords.LEFT_ANKLE.value].x, landmarks[coords.LEFT_ANKLE.value].y]
        
        hip_r = [landmarks[coords.RIGHT_HIP.value].x, landmarks[coords.RIGHT_HIP.value].y]
        knee_r = [landmarks[coords.RIGHT_KNEE.value].x, landmarks[coords.RIGHT_KNEE.value].y]
        ankle_r = [landmarks[coords.RIGHT_ANKLE.value].x, landmarks[coords.RIGHT_ANKLE.value].y]
        
        shoulder_l = np.array([landmarks[coords.LEFT_SHOULDER.value].x, landmarks[coords.LEFT_SHOULDER.value].y])
        shoulder_r = np.array([landmarks[coords.RIGHT_SHOULDER.value].x, landmarks[coords.RIGHT_SHOULDER.value].y])
        # --- FIX END ---

        avg_angle = (self.calculate_angle(hip_l, knee_l, ankle_l) + self.calculate_angle(hip_r, knee_r, ankle_r)) / 2

        knee_dist = np.linalg.norm(np.array(knee_l) - np.array(knee_r))
        shoulder_dist = np.linalg.norm(shoulder_l - shoulder_r)

        if knee_dist < shoulder_dist * 0.7:
            feedback['text'].append("Knees Out!"); feedback['arrows'].append("outward"); feedback['faulty_parts'].update(['left_leg', 'right_leg'])

        if avg_angle < 90:
            if self.current_stage == 'up':
                self.rep_counter += 1
                feedback['text'].append("Good Depth!")
            self.current_stage = "down"
        elif avg_angle > 160:
            self.current_stage = "up"
        
        if self.current_stage == 'up' and avg_angle < 160 and avg_angle > 90:
             feedback['text'].append("Squat Lower!"); feedback['arrows'].append("down"); feedback['faulty_parts'].update(['left_leg', 'right_leg'])

        self.feedback_dict = feedback

    def _handle_bicep_curl(self, landmarks):
        feedback = {'text': [], 'arrows': [], 'faulty_parts': set()}
        coords = self.mp_pose.PoseLandmark

        # --- FIX START ---
        shoulder_l = [landmarks[coords.LEFT_SHOULDER.value].x, landmarks[coords.LEFT_SHOULDER.value].y]
        elbow_l = [landmarks[coords.LEFT_ELBOW.value].x, landmarks[coords.LEFT_ELBOW.value].y]
        wrist_l = [landmarks[coords.LEFT_WRIST.value].x, landmarks[coords.LEFT_WRIST.value].y]
        # --- FIX END ---

        angle_l = self.calculate_angle(shoulder_l, elbow_l, wrist_l)
        if angle_l > 160:
            if self.current_stage == 'up': feedback['text'].append("Good Rep!")
            self.current_stage = "down"
        if self.current_stage == "down" and angle_l < 30:
            self.current_stage = "up"; self.rep_counter += 1
        self.feedback_dict = feedback
        
    def _draw_feedback(self, image, landmarks):
        image_h, image_w, _ = image.shape
        coords = self.mp_pose.PoseLandmark
        
        for txt in self.feedback_dict.get('text', []):
            is_positive = "Good" in txt
            box_color, text_color = (BLUE, BLACK) if is_positive else (RED, WHITE)
            text_size = cv2.getTextSize(txt, FONT, 0.8, 2)[0]
            cv2.rectangle(image, (5, 85), (15 + text_size[0], 125), box_color, -1)
            cv2.putText(image, txt, (10, 115), FONT, 0.8, text_color, 2)
            
        shoulder_l, shoulder_r = landmarks[coords.LEFT_SHOULDER.value], landmarks[coords.RIGHT_SHOULDER.value]
        hip_l, hip_r = landmarks[coords.LEFT_HIP.value], landmarks[coords.RIGHT_HIP.value]
        shoulder_mid_x = (shoulder_l.x + shoulder_r.x) / 2
        hip_mid_x = (hip_l.x + hip_r.x) / 2
        body_vector_y = np.array([hip_mid_x - shoulder_mid_x, (hip_l.y + hip_r.y)/2 - (shoulder_l.y + shoulder_r.y)/2])
        if np.linalg.norm(body_vector_y) > 0:
            body_vector_y = body_vector_y / np.linalg.norm(body_vector_y)
            
        if "down" in self.feedback_dict.get('arrows', []):
            hip, knee = landmarks[coords.LEFT_HIP.value], landmarks[coords.LEFT_KNEE.value]
            start_point = (int((hip.x + knee.x)/2 * image_w), int((hip.y + knee.y)/2 * image_h))
            end_point = (int(start_point[0] + body_vector_y[0] * 80), int(start_point[1] + body_vector_y[1] * 80))
            draw_arrow(image, start_point, end_point, "Lower!")

        if "outward" in self.feedback_dict.get('arrows', []):
            knee_l, ankle_l = landmarks[coords.LEFT_KNEE.value], landmarks[coords.LEFT_ANKLE.value]
            knee_r, ankle_r = landmarks[coords.RIGHT_KNEE.value], landmarks[coords.RIGHT_ANKLE.value]
            shin_vector_l = np.array([knee_l.x - ankle_l.x, knee_l.y - ankle_l.y])
            outward_vector_l = np.array([-shin_vector_l[1], shin_vector_l[0]])
            if np.linalg.norm(outward_vector_l) > 0: outward_vector_l /= np.linalg.norm(outward_vector_l)
            shin_vector_r = np.array([knee_r.x - ankle_r.x, knee_r.y - ankle_r.y])
            outward_vector_r = np.array([shin_vector_r[1], -shin_vector_r[0]])
            if np.linalg.norm(outward_vector_r) > 0: outward_vector_r /= np.linalg.norm(outward_vector_r)
            
            knee_l_pt = (int(knee_l.x * image_w), int(knee_l.y * image_h))
            end_l = (int(knee_l_pt[0] + outward_vector_l[0] * 80), int(knee_l_pt[1] + outward_vector_l[1] * 80))
            draw_arrow(image, knee_l_pt, end_l)
            knee_r_pt = (int(knee_r.x * image_w), int(knee_r.y * image_h))
            end_r = (int(knee_r_pt[0] + outward_vector_r[0] * 80), int(knee_r_pt[1] + outward_vector_r[1] * 80))
            draw_arrow(image, knee_r_pt, end_r)
            
    def process_frame(self, image):
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.pose.process(image_rgb)
        try:
            landmarks = results.pose_landmarks.landmark
            if self.exercise_mode == 'squat': self._handle_squat(landmarks)
            else: self._handle_bicep_curl(landmarks)
            self._draw_feedback(image, landmarks)
        except: self.feedback_dict = {}

        if self.show_skeleton and results.pose_landmarks:
            image_h, image_w, _ = image.shape
            landmarks = results.pose_landmarks.landmark
            faulty_parts = self.feedback_dict.get('faulty_parts', set())
            for part, connections in self.BODY_PARTS.items():
                color = RED if part in faulty_parts else GREEN
                for c in connections:
                    p1, p2 = landmarks[c[0]], landmarks[c[1]]
                    if p1.visibility > 0.5 and p2.visibility > 0.5:
                        pt1, pt2 = (int(p1.x * image_w), int(p1.y * image_h)), (int(p2.x * image_w), int(p2.y * image_h))
                        cv2.line(image, pt1, pt2, color, 2)
        return image, {'reps': self.rep_counter, 'stage': self.current_stage, 'feedback': self.feedback_dict}