#!/usr/bin/env python
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

# Grabbed from https://gitlab.com/nickvsnetworking/pyrtp

""" Encodes and decodes RTP packets """


def decode_rtp_packet(packet_bytes):
    """ Decodes a RTP packet """
    packet_vars = {}
    byte1 = packet_bytes[0:2]
    byte1 = int(byte1, 16)
    byte1 = format(byte1, 'b')
    packet_vars['version'] = int(byte1[0:2], 2)
    packet_vars['padding'] = int(byte1[2:3])
    packet_vars['extension'] = int(byte1[3:4])
    packet_vars['csi_count'] = int(byte1[4:8], 2)

    byte2 = packet_bytes[2:4]

    byte2 = int(byte2, 16)
    byte2 = format(byte2, 'b').zfill(8)
    packet_vars['marker'] = int(byte2[0:1])
    packet_vars['payload_type'] = int(byte2[1:8], 2)

    packet_vars['sequence_number'] = int(str(packet_bytes[4:8]), 16)

    packet_vars['timestamp'] = int(str(packet_bytes[8:16]), 16)

    packet_vars['ssrc'] = int(str(packet_bytes[16:24]), 16)

    packet_vars['payload'] = str(packet_bytes[24:])
    return packet_vars


def generate_rtp_packet(packet_vars):
    """ Encodes/Generates a RTP packet """
    version = str(format(packet_vars['version'], 'b').zfill(2))
    padding = str(packet_vars['padding'])
    extension = str(packet_vars['extension'])
    csi_count = str(format(packet_vars['csi_count'], 'b').zfill(4))
    byte1_body = int((version + padding + extension + csi_count), 2)
    byte1 = format(byte1_body, 'x').zfill(2)

    # Generate second byte of header as binary string:
    marker = str(packet_vars['marker'])
    payload_type = str(format(packet_vars['payload_type'], 'b').zfill(7))
    byte2 = format(int((marker + payload_type), 2), 'x').zfill(2)

    sequence_number = format(packet_vars['sequence_number'], 'x').zfill(4)

    timestamp = format(packet_vars['timestamp'], 'x').zfill(8)

    ssrc = str(format(packet_vars['ssrc'], 'x').zfill(8))

    payload = packet_vars['payload']

    packet = byte1 + byte2 + sequence_number + timestamp + ssrc + payload

    return packet

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
