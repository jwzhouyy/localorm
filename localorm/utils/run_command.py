import base64
import requests
import subprocess
import threading

from pathlib import Path


def async_run_command_workflows(command_workflows):
    """按批次执行命令工作流，每批次并发执行"""
    for batch_idx, batch in enumerate(command_workflows, 1):
        print(f"\n{'='*60}")
        print(f"Executing batch {batch_idx}/{len(command_workflows)}")
        print("\n".join(batch))
        print(f"{'='*60}\n")

        threads = []
        results = [None] * len(batch)
        exceptions = [None] * len(batch)
        semaphore = threading.Semaphore(8)

        def run_command(cmd, index):
            with semaphore:
                try:
                    process = subprocess.Popen(
                        cmd,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                    )

                    output_lines = []
                    for line in iter(process.stdout.readline, ''):
                        print(line, end='')
                        output_lines.append(line)

                    process.wait(timeout=120)
                    results[index] = (process.returncode, ''.join(output_lines))
                except Exception as e:
                    exceptions[index] = e

        # 启动所有线程
        for idx, cmd in enumerate(batch):
            thread = threading.Thread(target=run_command, args=(cmd, idx))
            thread.start()
            threads.append(thread)

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 检查错误
        for idx, (cmd, exception) in enumerate(zip(batch, exceptions)):
            if exception:
                raise RuntimeError(f"Command failed: {cmd}\nError: {exception}")

            returncode, output = results[idx]
            if returncode != 0:
                raise RuntimeError(f"Command failed with code {returncode}: {cmd}")

        print(f"\nBatch {batch_idx} completed successfully\n")
