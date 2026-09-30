from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Callable


SITE_URL = "https://benisland.neocities.org/petpet/"
BASE_DIR = Path(__file__).resolve().parent
IMAGE_DIR = BASE_DIR / "image"
OUTPUT_DIR = BASE_DIR / "output"
IMAGE_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
    ".svg",
    ".ico",
    ".avif",
}
UPLOAD_TIMEOUT = 20
EXPORT_TIMEOUT = 60


def find_images() -> list[Path]:
    """Return supported image files directly inside image/, in a stable order."""
    if not IMAGE_DIR.is_dir():
        return []
    return sorted(
        (
            path
            for path in IMAGE_DIR.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        ),
        key=lambda path: (path.name.casefold(), path.name),
    )


def wait_until(
    condition: Callable[[], bool], timeout: float, description: str
) -> None:
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.1)

    raise TimeoutError(f"等待{description}超时（{timeout:g} 秒）")


def configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")


def check_site(requests_module) -> None:
    response = requests_module.get(
        SITE_URL,
        headers={"User-Agent": "Mozilla/5.0 petpet-batch-generator/1.0"},
        timeout=(5, 20),
    )
    response.raise_for_status()

    required_markers = ('id="uploadFile"', 'id="export"', 'id="result"')
    if not all(marker in response.text for marker in required_markers):
        raise RuntimeError("网站页面结构已变化，未找到上传框、export 按钮或输出图片。")


def wait_for_page(page) -> None:
    wait_until(
        lambda: bool(
            page.run_js(
                """
                return document.readyState === 'complete'
                    && document.querySelector('#uploadFile')
                    && document.querySelector('#reset')
                    && document.querySelector('#export')
                    && document.querySelector('#result');
                """
            )
        ),
        UPLOAD_TIMEOUT,
        "网站控件加载",
    )


def upload_image(page, image_path: Path) -> None:
    page.ele("#reset").click()
    page.run_js(
        """
        const preview = document.querySelector('#uploadPreview');
        preview.removeAttribute('src');
        preview.classList.remove('error');
        document.querySelector('#uploadError').innerText = '';
        """
    )
    page.ele("#uploadFile").input(str(image_path))

    def loaded() -> bool:
        error_text = page.ele("#uploadError").text.strip()
        if error_text:
            raise RuntimeError(f"网站无法加载该图片：{error_text}")
        return bool(
            page.run_js(
                """
                const preview = document.querySelector('#uploadPreview');
                return preview
                    && preview.src.startsWith('data:image/')
                    && preview.complete
                    && preview.naturalWidth > 0
                    && preview.naturalHeight > 0;
                """
            )
        )

    wait_until(loaded, UPLOAD_TIMEOUT, f"图片 {image_path.name} 的预览加载")


def export_gif(page, image_path: Path) -> Path:
    page.run_js("document.querySelector('#result').removeAttribute('src');")
    export_button = page.ele("#export")
    export_button.click()

    def rendered() -> bool:
        return bool(
            page.run_js(
                """
                const button = document.querySelector('#export');
                const result = document.querySelector('#result');
                return button && !button.disabled && result
                    && result.src.startsWith('blob:')
                    && result.complete
                    && result.naturalWidth > 0;
                """
            )
        )

    wait_until(rendered, EXPORT_TIMEOUT, f"图片 {image_path.name} 的 GIF 导出")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    saved_path = Path(
        page.ele("#result").save(
            path=OUTPUT_DIR,
            name=f"{image_path.stem}.gif",
            timeout=UPLOAD_TIMEOUT,
            rename=True,
        )
    )

    try:
        if saved_path.read_bytes()[:6] not in (b"GIF87a", b"GIF89a"):
            raise RuntimeError("网站返回的文件不是有效 GIF。")
    except Exception:
        saved_path.unlink(missing_ok=True)
        raise

    return saved_path


def process_images(page, image_paths: list[Path]) -> tuple[list[Path], list[tuple[Path, str]]]:
    successes: list[Path] = []
    failures: list[tuple[Path, str]] = []

    for index, image_path in enumerate(image_paths, start=1):
        print(f"[{index}/{len(image_paths)}] 正在处理：{image_path.name}", flush=True)
        try:
            upload_image(page, image_path)
            saved_path = export_gif(page, image_path)
            successes.append(saved_path)
            print(f"    已保存：{saved_path.name}", flush=True)
        except Exception as exc:
            failures.append((image_path, str(exc)))
            print(f"    失败：{exc}", file=sys.stderr, flush=True)
            if index < len(image_paths):
                try:
                    page.get(SITE_URL, timeout=30)
                    wait_for_page(page)
                except Exception as reload_exc:
                    message = f"页面恢复失败，无法继续批处理：{reload_exc}"
                    print(f"    {message}", file=sys.stderr, flush=True)
                    for remaining in image_paths[index:]:
                        failures.append((remaining, message))
                    break

    return successes, failures


def main() -> int:
    configure_console()
    image_paths = find_images()
    if not image_paths:
        print(f"未在 {IMAGE_DIR} 中发现可处理的图片。")
        return 0

    try:
        import requests
        from DrissionPage import ChromiumOptions, ChromiumPage
    except ImportError as exc:
        print(
            f"缺少 Python 依赖：{exc.name}\n"
            "请执行：python -m pip install requests DrissionPage",
            file=sys.stderr,
        )
        return 2

    try:
        check_site(requests)
    except Exception as exc:
        print(f"网站可用性检查失败：{exc}", file=sys.stderr)
        return 2

    page = None
    successes: list[Path] = []
    failures: list[tuple[Path, str]] = []

    try:
        options = ChromiumOptions().auto_port()
        options.headless(False)
        page = ChromiumPage(options)
        page.set.timeouts(base=10, page_load=30, script=EXPORT_TIMEOUT)
        page.get(SITE_URL, timeout=30)
        wait_for_page(page)
        successes, failures = process_images(page, image_paths)
    except Exception as exc:
        print(f"浏览器初始化或页面加载失败：{exc}", file=sys.stderr)
        return 2
    finally:
        if page is not None:
            try:
                page.quit(timeout=5, force=True)
            except Exception as exc:
                print(f"警告：关闭临时浏览器失败：{exc}", file=sys.stderr)

    print("\n处理完成：")
    print(f"  成功：{len(successes)}")
    print(f"  失败：{len(failures)}")
    for path in successes:
        print(f"  输出：{path}")
    for image_path, reason in failures:
        print(f"  失败：{image_path.name} -> {reason}", file=sys.stderr)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
