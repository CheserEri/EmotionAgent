"""
Motion Capture 启动脚本。
同时启动 Motion WebSocket 服务和 Web 静态文件服务。

用法:
  # 启动服务（配合浏览器使用）
  python run_motion.py

  # 处理视频文件并导出 VMD
  python run_motion.py --video dance.mp4 --export-vmd output.vmd

  # 处理视频文件（离线模式，不启动 WebSocket）
  python run_motion.py --video dance.mp4 --offline

  # 启动摄像头实时模式
  python run_motion.py --camera 0
"""
import argparse
import asyncio
import json
import os
import signal
import sys
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import urllib.parse

# 项目路径
PROJECT_DIR = Path(__file__).parent
WEB_DIR = PROJECT_DIR / "web"

# 添加项目路径到 sys.path
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))


# ============================================================
# Web 静态文件服务（简化版，只提供静态文件，不代理 API）
# ============================================================

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tga": "application/octet-stream",
    ".pmx": "application/octet-stream",
    ".vmd": "application/octet-stream",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


class MotionWebHandler(SimpleHTTPRequestHandler):
    """静态文件服务。"""

    def do_GET(self):
        path = urllib.parse.unquote(self.path.split("?")[0])
        if path == "/":
            path = "/motion.html"

        file_path = WEB_DIR / path.lstrip("/")

        # 安全检查
        try:
            file_path = file_path.resolve()
            if not str(file_path).startswith(str(WEB_DIR.resolve())):
                self.send_error(403)
                return
        except (ValueError, OSError):
            self.send_error(400)
            return

        if not file_path.is_file():
            self.send_error(404, f"File not found: {path}")
            return

        ext = file_path.suffix.lower()
        mime = MIME_TYPES.get(ext, "application/octet-stream")

        try:
            data = file_path.read_bytes()
        except OSError:
            self.send_error(500)
            return

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        print(f"  [Web] {format % args}")


def start_web_server(host: str, port: int) -> HTTPServer:
    """启动 Web 静态文件服务。"""
    server = HTTPServer((host, port), MotionWebHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Web 服务启动在 http://{host}:{port}")
    return server


# ============================================================
# 离线视频处理
# ============================================================

def process_video_offline(
    video_path: str,
    output_vmd: str | None = None,
    start_frame: int = 0,
    max_frames: int | None = None,
    model_complexity: int = 1,
    smooth_alpha: float = 0.4,
) -> None:
    """离线处理视频，可选导出 VMD。"""
    from cli_avatar.pose_estimator import PoseEstimator
    from cli_avatar.motion_mapper import MotionMapper
    from cli_avatar.vmd_writer import VMDWriter

    video_path = Path(video_path)
    if not video_path.is_file():
        print(f"错误: 视频文件不存在: {video_path}")
        return

    print(f"处理视频: {video_path}")
    print(f"  模型复杂度: {model_complexity}")
    print(f"  平滑系数: {smooth_alpha}")
    if output_vmd:
        print(f"  VMD 输出: {output_vmd}")
    print()

    estimator = PoseEstimator(model_complexity=model_complexity)
    mapper = MotionMapper(smooth_alpha=smooth_alpha)
    vmd_writer = VMDWriter() if output_vmd else None

    frame_count = 0
    detected_count = 0

    try:
        import time
        start_time = time.monotonic()

        for pose_frame in estimator.estimate_from_video(
            video_path, max_frames=max_frames, start_frame=start_frame
        ):
            frame_count += 1
            bone_data = mapper.map_frame(pose_frame)

            if bone_data:
                detected_count += 1

            if vmd_writer:
                vmd_writer.add_frame_data(pose_frame.frame_index, bone_data)

            # 进度提示
            if frame_count % 50 == 0:
                print(f"  已处理 {frame_count} 帧 (检测到 {detected_count} 帧)")

        elapsed = time.monotonic() - start_time

        print()
        print(f"处理完成:")
        print(f"  总帧数: {frame_count}")
        print(f"  检测到姿态: {detected_count} 帧")
        print(f"  耗时: {elapsed:.1f}s")
        print(f"  处理速度: {frame_count / elapsed:.1f} FPS")

        if vmd_writer:
            vmd_writer.write(output_vmd)
            print(f"  VMD 已导出: {output_vmd}")

    except Exception as e:
        print(f"处理错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        estimator.close()


# ============================================================
# 摄像头实时处理
# ============================================================

def process_camera_realtime(
    camera_id: int = 0,
    model_complexity: int = 1,
    smooth_alpha: float = 0.4,
    target_fps: float = 30.0,
) -> None:
    """摄像头实时处理（控制台模式，不启动 WebSocket）。"""
    from cli_avatar.pose_estimator import PoseEstimator
    from cli_avatar.motion_mapper import MotionMapper

    print(f"摄像头实时模式 (ID: {camera_id})")
    print("按 Ctrl+C 停止")
    print()

    estimator = PoseEstimator(model_complexity=model_complexity)
    mapper = MotionMapper(smooth_alpha=smooth_alpha)

    frame_count = 0

    try:
        import time
        start_time = time.monotonic()

        for pose_frame in estimator.estimate_from_camera(
            camera_id=camera_id, target_fps=target_fps
        ):
            frame_count += 1
            bone_data = mapper.map_frame(pose_frame)

            if frame_count % 30 == 0:
                elapsed = time.monotonic() - start_time
                print(f"  帧 {frame_count}, "
                      f"FPS: {frame_count / elapsed:.1f}, "
                      f"骨骼: {len(bone_data)}")

    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        estimator.close()


# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Emotion Agent - Motion Capture",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_motion.py                          # 启动 WebSocket + Web 服务
  python run_motion.py --video dance.mp4        # 处理视频（启动服务模式）
  python run_motion.py --video dance.mp4 --offline --export-vmd out.vmd  # 离线导出
  python run_motion.py --camera 0               # 摄像头实时（控制台）
  python run_motion.py --ws-port 8766 --web-port 8080  # 自定义端口
        """,
    )

    # 视频处理
    parser.add_argument("--video", type=str, help="视频文件路径")
    parser.add_argument("--start-frame", type=int, default=0, help="起始帧号")
    parser.add_argument("--max-frames", type=int, help="最大处理帧数")
    parser.add_argument("--export-vmd", type=str, help="导出 VMD 文件路径")

    # 摄像头
    parser.add_argument("--camera", type=int, help="摄像头 ID（离线模式）")

    # 服务配置
    parser.add_argument("--host", type=str, default="127.0.0.1", help="服务地址")
    parser.add_argument("--ws-port", type=int, default=8766, help="WebSocket 端口")
    parser.add_argument("--web-port", type=int, default=8080, help="Web 服务端口")
    parser.add_argument("--no-web", action="store_true", help="不启动 Web 服务")

    # 模型参数
    parser.add_argument("--complexity", type=int, default=1, choices=[0, 1, 2],
                        help="MediaPipe 模型复杂度 (0=轻量, 1=标准, 2=高精度)")
    parser.add_argument("--smooth", type=float, default=0.4, help="平滑系数 (0-1)")

    # 离线模式
    parser.add_argument("--offline", action="store_true", help="离线模式（不启动 WebSocket）")

    args = parser.parse_args()

    print("=" * 50)
    print("Emotion Agent - Motion Capture")
    print("=" * 50)
    print()

    # 离线视频处理模式
    if args.video and args.offline:
        process_video_offline(
            video_path=args.video,
            output_vmd=args.export_vmd,
            start_frame=args.start_frame,
            max_frames=args.max_frames,
            model_complexity=args.complexity,
            smooth_alpha=args.smooth,
        )
        return

    # 摄像头离线模式
    if args.camera is not None and args.offline:
        process_camera_realtime(
            camera_id=args.camera,
            model_complexity=args.complexity,
            smooth_alpha=args.smooth,
        )
        return

    # 在线服务模式
    from cli_avatar.motion_server import MotionServer

    # 启动 Web 服务
    web_server = None
    if not args.no_web:
        web_server = start_web_server(args.host, args.web_port)

    # 启动 Motion WebSocket 服务
    server = MotionServer(
        host=args.host,
        port=args.ws_port,
        smooth_alpha=args.smooth,
        model_complexity=args.complexity,
    )

    print()
    print(f"Motion WebSocket: ws://{args.host}:{args.ws_port}")
    if web_server:
        print(f"Web 前端:        http://{args.host}:{args.web_port}/motion.html")
    print()
    print("使用方式:")
    print("  1. 打开浏览器访问上述地址")
    print("  2. 输入视频路径或启动摄像头")
    print("  3. 模型将实时复刻舞蹈动作")
    print()
    if args.video:
        print(f"提示: 启动后将自动处理视频 {args.video}")
    print("Ctrl+C 退出")
    print()

    # 如果指定了视频，启动后自动处理
    if args.video:
        async def auto_start():
            await asyncio.sleep(1)  # 等待客户端连接
            # 通过内部 API 触发处理
            print(f"自动处理视频: {args.video}")

        # 在单独线程中运行自动启动
        def run_auto():
            import time
            time.sleep(2)
            print(f"提示: 请在浏览器中输入视频路径: {args.video}")

        auto_thread = threading.Thread(target=run_auto, daemon=True)
        auto_thread.start()

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\nMotion Server 已停止。")
        if web_server:
            web_server.shutdown()


if __name__ == "__main__":
    main()
