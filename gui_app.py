# gui_app.py

import cv2
import customtkinter as ctk
from PIL import Image, ImageTk
from PoseEngine import PoseEngine # 导入我们刚刚创建的引擎

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- 窗口设置 ---
        self.title("AI Fitness Coach")
        self.geometry("1200x800")
        ctk.set_appearance_mode("dark")

        # --- 状态变量 ---
        self.cap = None
        self.is_video_running = False
        
        # --- 实例化姿态引擎 ---
        self.pose_engine = PoseEngine()


        # --- 创建UI组件 ---
        # 顶部框架
        self.top_frame = ctk.CTkFrame(self, height=80)
        self.top_frame.pack(fill="x", padx=10, pady=10)

        # 视频显示标签
        self.video_label = ctk.CTkLabel(self, text="")
        self.video_label.pack(fill="both", expand=True, padx=10, pady=10)
        
        # --- 顶部框架内的组件 ---
        self.start_stop_button = ctk.CTkButton(self.top_frame, text="Start", command=self.toggle_video)
        self.start_stop_button.pack(side="left", padx=10, pady=10)

        # --- 新增：骨架切换按钮 ---
        self.skeleton_button = ctk.CTkButton(self.top_frame, text="Hide Skeleton", command=self.toggle_skeleton_view)
        self.skeleton_button.pack(side="left", padx=10, pady=10)

        self.squat_button = ctk.CTkButton(self.top_frame, text="Squat Mode", command=lambda: self.set_mode('squat'))
        self.squat_button.pack(side="left", padx=10, pady=10)

        self.bicep_button = ctk.CTkButton(self.top_frame, text="Bicep Curl Mode", command=lambda: self.set_mode('bicep_curl'))
        self.bicep_button.pack(side="left", padx=10, pady=10)
        
        # Reps 和 Stage 显示
        self.reps_label = ctk.CTkLabel(self.top_frame, text="REPS: 0", font=("Arial", 24))
        self.reps_label.pack(side="right", padx=20, pady=10)
        
        self.stage_label = ctk.CTkLabel(self.top_frame, text="STAGE: -", font=("Arial", 24))
        self.stage_label.pack(side="right", padx=20, pady=10)

    def toggle_video(self):
        if self.is_video_running:
            # 停止视频
            self.is_video_running = False
            self.start_stop_button.configure(text="Start")
            if self.cap:
                self.cap.release()
            self.video_label.configure(image=None)
        else:
            # 开始视频
            try:
                self.cap = cv2.VideoCapture(0)
                if not self.cap.isOpened():
                    raise IOError("Cannot open webcam")
                self.is_video_running = True
                self.start_stop_button.configure(text="Stop")
                self.update_frame()
            except IOError as e:
                print(e)
                # 你可以在这里弹出一个错误窗口
    
    def set_mode(self, mode):
        self.pose_engine.set_mode(mode)
        # 重置UI上的计数器和状态
        self.reps_label.configure(text="REPS: 0")
        self.stage_label.configure(text=f"STAGE: {self.pose_engine.current_stage.upper()}")


    # --- 新增：骨架按钮的响应函数 ---
    def toggle_skeleton_view(self):
        is_showing = self.pose_engine.toggle_skeleton()
        if is_showing:
            self.skeleton_button.configure(text="Hide Skeleton")
        else:
            self.skeleton_button.configure(text="Show Skeleton")
    

    def update_frame(self):
        if not self.is_video_running or not self.cap.isOpened():
            return

        ret, frame = self.cap.read()
        if ret:
            # --- 关键改动：在这里实现镜面效果 ---
            frame = cv2.flip(frame, 1)

            # 1. 将翻转后的帧交给引擎处理
            processed_frame, feedback_data = self.pose_engine.process_frame(frame) # 返回值已简化

            
            # --- 在这里可以添加绘制逻辑，或者把绘制逻辑也封装到引擎里 ---
            # (为了简化，我们将保持上一个版本的绘制逻辑，并在此处调用)
            # 在此省略了复杂的绘制代码，因为它们可以被包含在引擎处理的一部分
            # 我们只需要显示最终的 processed_frame

            # 2. 更新UI上的数据显示
            self.reps_label.configure(text=f"REPS: {feedback_data['reps']}")
            self.stage_label.configure(text=f"STAGE: {feedback_data['stage'].upper()}")

            # 3. 将OpenCV图像转换为Tkinter图像
            img = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img)
            img_tk = ctk.CTkImage(light_image=img_pil, dark_image=img_pil, size=(img_pil.width, img_pil.height))
            
            self.video_label.configure(image=img_tk)
            self.video_label.image = img_tk
        
        # 4. 安排下一帧的更新
        self.after(15, self.update_frame)

    def on_closing(self):
        if self.cap:
            self.cap.release()
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()