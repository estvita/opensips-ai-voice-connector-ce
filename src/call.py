#
# Copyright (C) 2024 SIP Point Consulting SRL
#
# This file is part of the OpenSIPS AI Voice Connector project
# (see https://github.com/OpenSIPS/opensips-ai-voice-connector-ce).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

""" Handles the a SIP call """

import random
import socket
import asyncio
import logging
import datetime
from queue import Queue, Empty
from aiortc.sdp import SessionDescription
from config import Config

from rtp import decode_rtp_packet, generate_rtp_packet
from utils import get_ai


class Call():  # pylint: disable=too-many-instance-attributes
    """ Class that handles a call """
    def __init__(self,  # pylint: disable=too-many-arguments
                 b2b_key, sdp: SessionDescription,
                 flavor: str):
        try:
            hostname = socket.gethostbyname(socket.gethostname())
        except socket.gaierror:  # unknown hostname
            hostname = "127.0.0.1"
        host_ip = Config.engine('rtp_ip', 'RTP_IP', hostname)

        self.b2b_key = b2b_key

        if sdp.media[0].host:
            self.client_addr = sdp.media[0].host
        else:
            self.client_addr = sdp.host
        self.client_port = sdp.media[0].port
        self.paused = False

        self.rtp = Queue()
        self.stop_event = asyncio.Event()
        self.stop_event.clear()

        self.ai = get_ai(flavor, b2b_key, sdp, self.rtp)

        self.codec = self.ai.get_codec()

        self.serversock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.serversock.bind((host_ip, 0))

        self.sdp = self.get_new_sdp(sdp, host_ip)

        asyncio.create_task(self.ai.start())

        loop = asyncio.get_running_loop()
        loop.add_reader(self.serversock.fileno(), self.read_rtp)
        asyncio.create_task(self.send_rtp())
        logging.info("handling %s using %s AI", b2b_key, flavor)

    def get_body(self):
        """ Retrieves the SDP built """
        return str(self.sdp)

    def get_new_sdp(self, sdp, host_ip):
        """ Gets a new SDP to be sent back in 200 OK """
        sdp.origin = f"{sdp.origin.rsplit(' ', 1)[0]} {host_ip}"
        sdp.media[0].port = self.serversock.getsockname()[1]
        if sdp.host:
            sdp.host = host_ip
        if sdp.media[0].host:
            sdp.media[0].host = host_ip

        # update SDP to return only chosen codec
        # as we do not accept anything else
        # Remove all other codecs
        sdp.media[0].rtp.codecs = [self.codec.params]
        sdp.media[0].fmt = [self.codec.payload_type]

        return sdp

    def resume(self):
        """ Resumes the call's audio """
        if not self.paused:
            return
        logging.info("resuming %s", self.b2b_key)
        self.paused = False
        self.sdp.media[0].direction = "sendrecv"

    def pause(self):
        """ Pauses the call's audio """
        if self.paused:
            return
        logging.info("pausing %s", self.b2b_key)
        self.sdp.media[0].direction = "recvonly"

        self.paused = True

    def read_rtp(self):
        """ Reads a RTP packet """
        data = self.serversock.recv(1024)
        # Drop requests if paused
        if self.paused:
            return
        try:
            packet = decode_rtp_packet(data.hex())
            audio = bytes.fromhex(packet['payload'])
            asyncio.create_task(self.ai.send(audio))
        except ValueError:
            pass

    async def send_rtp(self):
        """ Sends all RTP packet """

        sequence_number = random.randint(0, 10000)
        timestamp = random.randint(0, 10000)
        ssrc = random.randint(0, 2**31)
        ts_inc = self.codec.ts_increment
        ptime = self.codec.ptime
        payload_type = self.codec.payload_type
        marker = 1

        while not self.stop_event.is_set():
            last_time = datetime.datetime.now()
            try:
                payload = self.rtp.get_nowait()
            except Empty:
                if not self.paused:
                    payload = self.codec.get_silence()
                else:
                    payload = None
            if payload:
                rtp_packet = generate_rtp_packet({
                    'version': 2,
                    'padding': 0,
                    'extension': 0,
                    'csi_count': 0,
                    'marker': marker,
                    'payload_type': payload_type,
                    'sequence_number': sequence_number,
                    'timestamp': timestamp,
                    'ssrc': ssrc,
                    'payload': payload.hex()
                })
                marker = 0
                sequence_number += 1
                self.serversock.sendto(bytes.fromhex(rtp_packet),
                                       (self.client_addr, self.client_port))
            timestamp += ts_inc
            next_time = last_time + datetime.timedelta(milliseconds=ptime)
            now = datetime.datetime.now()
            drift = (next_time - now).total_seconds()
            if drift > 0:
                await asyncio.sleep(float(drift))

    async def close(self):
        """ Closes the call """
        logging.info("Call %s closing", self.b2b_key)
        loop = asyncio.get_running_loop()
        loop.remove_reader(self.serversock.fileno())
        self.serversock.close()
        self.stop_event.set()
        await self.ai.close()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
