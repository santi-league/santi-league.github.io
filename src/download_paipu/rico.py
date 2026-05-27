#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Download Mahjong Soul paipu using ricochet.cn API
API endpoint: https://ricochet.cn/api/naga/generate_tenhou
"""

import requests
import json
from typing import Optional


class RicochetDownloader:
    """Download Mahjong Soul paipu and convert to Tenhou format using ricochet.cn API"""

    BASE_URL = "https://ricochet.cn"
    API_ENDPOINT = "/api/naga/generate_tenhou"
    LOGIN_ENDPOINT = "/api/login"

    def __init__(self, timeout: int = 30):
        """
        Initialize downloader

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self.token = None

    def login(self, username: str, password: str):
        """
        Login to ricochet.cn

        Args:
            username: Username
            password: Password

        Raises:
            ValueError: Login failed
        """
        url = f"{self.BASE_URL}{self.LOGIN_ENDPOINT}"

        data = {
            'username': username,
            'password': password
        }

        try:
            response = self.session.post(url, data=data, timeout=self.timeout)
            response.raise_for_status()

            result = response.json()

            if result.get('status') != 1:
                error_msg = result.get('msg', 'Unknown error')
                raise ValueError(f"Login failed: {error_msg}")

            self.token = result.get('token')
            if self.token:
                self.session.headers.update({
                    'Authorization': f'token {self.token}'
                })

            print(f"Login successful as {username}")

        except requests.RequestException as e:
            raise ValueError(f"Login request failed: {e}")

    def download(self, paipu_url: str, account_id: str = '1497') -> list:
        """
        Download and convert paipu

        Args:
            paipu_url: Full Mahjong Soul paipu URL, e.g. "https://game.maj-soul.com/1/?paipu=..."
            account_id: Account ID (default: '1497')

        Returns:
            List of paipu data in Tenhou format

        Raises:
            requests.RequestException: Network request failed
            ValueError: API returned error or invalid data format, or not logged in
        """
        if not self.token:
            raise ValueError("Must login first before downloading")

        url = f"{self.BASE_URL}/api/naga/analyze_majsoul_step1"

        # Construct request data with required parameters
        data = {
            'url': paipu_url,
            'id': account_id,
            'ret_format': 'v2',
            'src': 'mjs'
        }

        try:
            response = self.session.post(
                url,
                data=data,
                timeout=self.timeout
            )
            response.raise_for_status()

            result = response.json()

            # Check return status
            if result.get('status') != 1:
                error_msg = result.get('msg', 'Unknown error')
                raise ValueError(f"API error: {error_msg}")

            # Return data
            paipu_data = result.get('data')
            if not paipu_data:
                raise ValueError("No paipu data in response")

            return paipu_data

        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to download paipu: {e}")

    def download_to_file(self, paipu_url: str, output_path: str, account_id: str = '1497', pretty: bool = True):
        """
        Download paipu and save to file

        Args:
            paipu_url: Full Mahjong Soul paipu URL
            output_path: Output file path
            account_id: Account ID (default: '1497')
            pretty: Whether to format JSON (default True)
        """
        paipu = self.download(paipu_url, account_id)

        with open(output_path, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(paipu, f, ensure_ascii=False, indent=2)
            else:
                json.dump(paipu, f, ensure_ascii=False)

        print(f"Paipu saved to {output_path}")

    def close(self):
        """Close session"""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def main():
    """Example usage"""
    # Full Mahjong Soul paipu URL
    paipu_url = "https://game.maj-soul.com/1/?paipu=260527-68e20453-53ad-485a-89ec-93d2d72c88bd_a259233423"

    # Login credentials
    username = "your_username"
    password = "your_password"

    # Method 1: Download and print
    with RicochetDownloader() as downloader:
        downloader.login(username, password)
        paipu_list = downloader.download(paipu_url)
        print(f"Downloaded {len(paipu_list)} rounds")
        print(json.dumps(paipu_list[0], ensure_ascii=False, indent=2)[:500])

    # Method 2: Save directly to file
    # with RicochetDownloader() as downloader:
    #     downloader.login(username, password)
    #     downloader.download_to_file(paipu_url, "paipu.json")


if __name__ == "__main__":
    main()
