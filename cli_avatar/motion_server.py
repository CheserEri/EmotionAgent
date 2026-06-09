"""
WebSocket 服务模块。
实时推送骨骼动画数据到前端。
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import websockets
from websockets.server import serve, WebSocketServerProtocol

from cli_avatar.pose_estimator import PoseEstimator, PoseFrame
from cli_avatar.motion_mapper import MotionMapper
from cli_avatar.vmd_writer import VMDWriter


class MotionServer:
    """WebSocket 服务，实时推送骨骼数据。"""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8766,
        smooth_alpha: float = 0.4,
        model_complexity: int = 1,
    ):
        self.host = host
        self.port = port
        self.smooth_alpha = smooth_alpha
        self.model_complexity = model_complexity

        self._clients: set[WebSocketServerProtocol] = set()
        self._running = False
        self._current_task: asyncio.Task | None = None

    async def start(self) -> None:
        """启动 WebSocket 服务。"""
        print(f"Motion WebSocket 服务启动在 ws://{self.host}:{self.port}")
        print("  客户端可连接此地址接收骨骼数据")
        print("Ctrl+C 退出")

        async with serve(self._handler, self.host, self.port):
            self._running = True
            await asyncio.Future()  # 永久运行

    async def _handler(self, websocket: WebSocketServerProtocol) -> None:
        """处理 WebSocket 连接。"""
        self._clients.add(websocket)
        client_addr = websocket.remote_address
        print(f"客户端已连接: {client_addr}")

        try:
            async for message in websocket:
                await self._handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self._clients.discard(websocket)
            print(f"客户端已断开: {client_addr}")

    async def _handle_message(self, ws: WebSocketServerProtocol, message: str) -> None:
        """处理客户端消息。"""
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            await ws.send(json.dumps({"error": "无效的 JSON"}))
            return

        command = data.get("command")

        if command == "process_video":
            video_path = data.get("path", "")
            start_frame = data.get("start_frame", 0)
            max_frames = data.get("max_frames", None)
            export_vmd = data.get("export_vmd", None)

            if not video_path:
                await ws.send(json.dumps({"error": "缺少视频路径"}))
                return

            # 取消之前的任务
            if self._current_task and not self._current_task.done():
                self._current_task.cancel()

            self._current_task = asyncio.create_task(
                self._process_video(ws, video_path, start_frame, max_frames, export_vmd)
            )

        elif command == "start_camera":
            camera_id = data.get("camera_id", 0)
            target_fps = data.get("fps", 30.0)

            if self._current_task and not self._current_task.done():
                self._current_task.cancel()

            self._current_task = asyncio.create_task(
                self._process_camera(ws, camera_id, target_fps)
            )

        elif command == "stop":
            if self._current_task and not self._current_task.done():
                self._current_task.cancel()
                await ws.send(json.dumps({"type": "stopped"}))

        elif command == "ping":
            await ws.send(json.dumps({"type": "pong"}))

        else:
            await ws.send(json.dumps({"error": f"未知命令: {command}"}))

    async def _process_video(
        self,
        ws: WebSocketServerProtocol,
        video_path: str,
        start_frame: int = 0,
        max_frames: int | None = None,
        export_vmd: str | None = None,
    ) -> None:
        """处理视频文件并推送骨骼数据。"""
        try:
            estimator = PoseEstimator(model_complexity=self.model_complexity)
            mapper = MotionMapper(smooth_alpha=self.smooth_alpha)
            vmd_writer = VMDWriter() if export_vmd else None

            await ws.send(json.dumps({
                "type": "start",
                "source": "video",
                "path": video_path,
            }))

            frame_count = 0
            start_time = time.monotonic()

            for pose_frame in estimator.estimate_from_video(
                video_path, max_frames=max_frames, start_frame=start_frame
            ):
                # 转换为骨骼数据
                bone_data = mapper.map_frame(pose_frame)

                # 推送到前端
                msg = {
                    "type": "frame",
                    "frame": pose_frame.frame_index,
                    "timestamp": pose_frame.timestamp,
                    "bones": bone_data,
                }
                await ws.send(json.dumps(msg))

                # 收集 VMD 数据
                if vmd_writer:
                    vmd_writer.add_frame_data(pose_frame.frame_index, bone_data)

                frame_count += 1

                # 让出控制权，允许处理其他消息
                await asyncio.sleep(0)

            # 导出 VMD
            if vmd_writer and export_vmd:
                vmd_writer.write(export_vmd)

            elapsed = time.monotonic() - start_time
            await ws.send(json.dumps({
                "type": "complete",
                "frames": frame_count,
                "elapsed": round(elapsed, 2),
                "fps": round(frame_count / elapsed, 1) if elapsed > 0 else 0,
            }))

            estimator.close()
            print(f"视频处理完成: {frame_count} 帧, {elapsed:.1f}s")

        except asyncio.CancelledError:
            await ws.send(json.dumps({"type": "stopped"}))
        except Exception as e:
            await ws.send(json.dumps({"type": "error", "message": str(e)}))
            print(f"视频处理错误: {e}")

    async def _process_camera(
        self,
        ws: WebSocketServerProtocol,
        camera_id: int = 0,
        target_fps: float = 30.0,
    ) -> None:
        """处理摄像头实时数据。"""
        try:
            estimator = PoseEstimator(model_complexity=self.model_complexity)
            mapper = MotionMapper(smooth_alpha=self.smooth_alpha)

            await ws.send(json.dumps({
                "type": "start",
                "source": "camera",
                "camera_id": camera_id,
            }))

            frame_count = 0
            start_time = time.monotonic()

            for pose_frame in estimator.estimate_from_camera(
                camera_id=camera_id, target_fps=target_fps
            ):
                bone_data = mapper.map_frame(pose_frame)

                msg = {
                    "type": "frame",
                    "frame": pose_frame.frame_index,
                    "timestamp": pose_frame.timestamp,
                    "bones": bone_data,
                }
                await ws.send(json.dumps(msg))

                frame_count += 1
                await asyncio.sleep(0)

            estimator.close()

        except asyncio.CancelledError:
            await ws.send(json.dumps({"type": "stopped"}))
        except Exception as e:
            await ws.send(json.dumps({"type": "error", "message": str(e)}))
            print(f"摄像头处理错误: {e}")

    def stop(self) -> None:
        """停止服务。"""
        self._running = False
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()


def run_motion_server(
    host: str = "127.0.0.1",
    port: int = 8766,
    smooth_alpha: float = 0.4,
    model_complexity: int = 1,
) -> None:
    """启动 Motion WebSocket 服务（同步入口）。"""
    server = MotionServer(
        host=host,
        port=port,
        smooth_alpha=smooth_alpha,
        model_complexity=model_complexity,
    )
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\nMotion Server 已停止。")
