from pathlib import Path

import requests
from Crypto.Cipher import AES
import httpx

from utils import ts2mp4


def add_to_16(value):
    while len(value) % 16 != 0:
        value += '\0'
    return str.encode(value)


def decrypt(ciphertext, key):
    iv = ciphertext[:AES.block_size]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    plaintext = cipher.decrypt(ciphertext[AES.block_size:])
    return plaintext.rstrip(b"\0")


def decrypt_file(filename, key):
    with open(filename, 'rb') as f:
        ciphertext = f.read()
    dec = decrypt(ciphertext, key)
    with open(filename, 'wb') as f:
        f.write(dec)


def get_key(filename):
    with open(filename, 'rb') as f:
        key = f.read()
    return key


def download(file_url, file):
    res = requests.get(file_url)
    with open(file, 'wb') as f:
        f.write(res.content)
    return 0


def lg_download(file_url, filename, path, headers=None):
    # 用来下载大文件，有进度条
    file = str(Path(path, filename))
    response = requests.get(file_url, stream=True, headers=headers)
    size = 0
    chunk_size = 1024
    content_size = int(response.headers['content-length'])
    if response.status_code == 200:
        print('正在下载 {filename},大小: {size:.2f} MB'.format(filename=filename,
                                                         size=content_size / chunk_size / 1024))
        with open(file, 'wb') as file:
            for data in response.iter_content(chunk_size=chunk_size):
                file.write(data)
                size += len(data)
                print('\r' + '[下载进度]:%s %.2f%%' % ('▋' * int(size * 50 / content_size),
                                                   float(size / content_size * 100)), end='')


async def async_download(url, path: Path, filename):
    client = httpx.AsyncClient(timeout=httpx.Timeout(10, connect=5, read=5, write=5, pool=5))
    filename_ext = filename + '.ts'
    base_file = path.joinpath(filename_ext)
    size = 0
    async with client.stream('GET', url) as response:
        content_size = int(response.headers['content-length'])
        if base_file.exists():
            if base_file.stat().st_size == content_size:
                return

        with open(base_file, 'wb') as file:
            current_size = 0
            async for chunk in response.aiter_bytes(chunk_size=1024):
                file.write(chunk)
                size += len(chunk)
                if size > current_size:
                    current_size = max(size, current_size)
                    print('\r\n' + filename + '[下载进度]:%s %.2f%%' % ('▋' * int(current_size * 50 / content_size),
                                                              float(current_size / content_size * 100)))
    await client.aclose()


def _download(url, path: Path, filename):
    client = httpx.Client(timeout=httpx.Timeout(10, connect=5, read=5, write=5, pool=5))
    filename_ext = filename + '.ts'
    base_file = path.joinpath(filename_ext)
    size = 0
    with client.stream('GET', url) as response:
        content_size = int(response.headers['content-length'])
        if base_file.exists() and base_file.stat().st_size == content_size:
            return
        with open(base_file, 'wb') as file:
            current_size = 0
            for chunk in response.iter_bytes():
                file.write(chunk)
                size += len(chunk)
                current_size = size
                print('\r\n' + filename + '[下载进度]:%s %.2f%%' % ('▋' * int(current_size * 50 / content_size),
                                                              float(current_size / content_size * 100)), end='')


async def download_single(ts_url, key_url, filename, path):
    print(filename,'开始下载')
    filename = filename.replace('/', '／').replace('\\', '＼')
    file:Path = path.joinpath(filename)
    final_video_name = file.name.split('.')[0] + ".mp4"
    if file.parent.joinpath(final_video_name).exists():
        print(final_video_name + '已存在！')
        return
    await async_download(ts_url, path, filename)
    # _download(ts_url, path, filename)
    download(file_url=key_url, file=file)
    key = get_key(file)
    decrypt_file(str(file) + '.ts', key)
    file.unlink()
    ts2mp4(str(file) + '.ts')
    print('\n' + filename + ' 下载完成！')
