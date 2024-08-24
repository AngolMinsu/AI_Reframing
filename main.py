import cv2
import mediapipe as mp
from moviepy.editor import ImageSequenceClip
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np

# Mediapipe 초기화 (Pose)
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()

# 글로벌 변수 설정
cap = None
frame_width = 0
frame_height = 0
total_frames = 0
processed_frames = []
target_aspect_ratio = 9 / 16  # 기본 비율 (9:16)
fixed_width = 0
fixed_height = 0
previous_frame = None  # 이전 프레임 저장

# 프레임 처리 함수
def process_frame(frame):
    global frame_width, frame_height, fixed_width, fixed_height, previous_frame
    frame_rgb = cv2.cvtColor(frame,cv2.COLOR_RGB2BGR)
    result = pose.process(frame_rgb)

    if result.pose_landmarks:
        x_min, y_min = frame_width, frame_height
        x_max, y_max = 0, 0

        # 주요 객체(몸체)의 영역을 감지
        for landmark in result.pose_landmarks.landmark:
            x = int(landmark.x * frame_width)
            y = int(landmark.y * frame_height)

            if x < x_min: x_min = x
            if y < y_min: y_min = y
            if x > x_max: x_max = x
            if y > y_max: y_max = y

        center_x = (x_min + x_max) // 2
        new_width = int(frame_height * target_aspect_ratio)
        x_min = max(0, center_x - new_width // 2)
        x_max = min(frame_width, center_x + new_width // 2)

        reframe = frame[:, x_min:x_max]
    else:
        # 객체를 감지하지 못한 경우 기본 중앙 부분을 크롭
        new_width = int(frame_height * target_aspect_ratio)
        reframe = frame[:, (frame_width-new_width)//2:(frame_width+new_width)//2]

    # 프레임 크기를 고정된 크기로 리사이즈
    reframe = cv2.resize(reframe, (fixed_width, fixed_height), interpolation=cv2.INTER_LINEAR)

    # 이전 프레임과 부드러운 전환을 위한 보정
    if previous_frame is not None:
        alpha = 0.7
        beta = 1 - alpha
        reframe = cv2.addWeighted(reframe, alpha, previous_frame, beta, 0)
    
    previous_frame = reframe

    return reframe

# 동영상 처리 함수
def process_video():
    global cap, processed_frames
    if cap and cap.isOpened():
        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            processed_frame = process_frame(frame)
            processed_frames.append(processed_frame)
            frame_count += 1
            progress_var.set(int((frame_count / total_frames) * 100))
            window.update_idletasks()
        cap.release()
        progress_var.set(100)
        messagebox.showinfo("Success", "동영상 리프레임 완료!")

# 동영상 저장 함수
def save_video():
    output_video_path = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 files", "*.mp4")])
    if output_video_path:
        if processed_frames:
            try:
                # 'libx264' 코덱을 사용하여 저장, 높은 품질 유지
                clip = ImageSequenceClip(processed_frames, fps=24)
                clip.write_videofile(output_video_path, codec="libx264", preset="slow", ffmpeg_params=["-crf", "18", "-preset", "slow"])
                messagebox.showinfo("Success", f"동영상이 성공적으로 저장되었습니다: {output_video_path}")
            except Exception as e:
                messagebox.showerror("Error", f"동영상 저장 중 오류가 발생했습니다: {str(e)}")
        else:
            messagebox.showwarning("Warning", "리프레임된 프레임이 없습니다. 동영상을 먼저 처리해 주세요.")

# 동영상 선택 함수
def select_video():
    global cap, frame_width, frame_height, total_frames, processed_frames, fixed_width, fixed_height
    video_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4;*.avi;*.mov")])
    if video_path:
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # 첫 번째 프레임을 읽어 비율 설정
            ret, first_frame = cap.read()
            if ret:
                # 9:16 비율에 맞게 첫 프레임 크기 결정
                fixed_width = int(frame_height * target_aspect_ratio)
                fixed_height = frame_height
                processed_frames.clear()  # 처리된 프레임 초기화
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # 비디오를 처음으로 되돌림

                # 리프레임 처리 시작
                process_video()
                btn_save.config(state=tk.NORMAL)
        else:
            messagebox.showerror("Error", "Cannot open the selected video file.")
            cap = None

# 비율 선택 함수
def set_aspect_ratio(aspect_ratio):
    global target_aspect_ratio
    target_aspect_ratio = aspect_ratio

# GUI 구성
window = tk.Tk()
window.title("AI Video Reframing Tool")

# 동영상 처리 진행 상황 표시
progress_var = tk.IntVar()
progress_bar = ttk.Progressbar(window, variable=progress_var, maximum=100, length=400)
progress_bar.grid(row=0, column=0, columnspan=3, pady=10)

btn_save = ttk.Button(window, text="동영상 저장", command=save_video, state=tk.DISABLED)
btn_save.grid(row=1, column=1, sticky="ew")

btn_select = ttk.Button(window, text="동영상 선택", command=select_video)
btn_select.grid(row=2, column=0, columnspan=3, sticky="ew")

# 비율 선택 버튼들
btn_ratio_16_9 = ttk.Button(window, text="16:9", command=lambda: set_aspect_ratio(16 / 9))
btn_ratio_16_9.grid(row=3, column=0, sticky="ew")

btn_ratio_9_16 = ttk.Button(window, text="9:16", command=lambda: set_aspect_ratio(9 / 16))
btn_ratio_9_16.grid(row=3, column=1, sticky="ew")

btn_ratio_1_1 = ttk.Button(window, text="1:1", command=lambda: set_aspect_ratio(1 / 1))
btn_ratio_1_1.grid(row=3, column=2, sticky="ew")

# Tkinter 윈도우 실행
window.mainloop()
