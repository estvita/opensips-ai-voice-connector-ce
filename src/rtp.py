def DecodeRTPpacket(packet_bytes):
    packet_vars = {}
    byte1 = packet_bytes[0:2]           #Byte1 as Hex
    byte1 = int(byte1, 16)              #Convert to Int
    byte1 = format(byte1, 'b')          #Convert to Binary
    packet_vars['version'] = int(byte1[0:2], 2)     #Get RTP Version
    packet_vars['padding'] = int(byte1[2:3])        #Get padding bit
    packet_vars['extension'] = int(byte1[3:4])        #Get extension bit
    packet_vars['csi_count'] = int(byte1[4:8], 2)     #Get RTP Version

    byte2 = packet_bytes[2:4]

    byte2 = int(byte2, 16)              #Convert to Int
    byte2 = format(byte2, 'b').zfill(8) #Convert to Binary
    packet_vars['marker'] = int(byte2[0:1])
    packet_vars['payload_type'] = int(byte2[1:8], 2)

    packet_vars['sequence_number'] = int(str(packet_bytes[4:8]), 16)

    packet_vars['timestamp'] = int(str(packet_bytes[8:16]), 16)

    packet_vars['ssrc'] = int(str(packet_bytes[16:24]), 16)

    packet_vars['payload'] = str(packet_bytes[24:])
    return packet_vars

def GenerateRTPpacket(packet_vars):
    version = str(format(packet_vars['version'], 'b').zfill(2))                  #RFC189 Version (Typically 2)
    padding = str(packet_vars['padding'])                                        #Padding (Typically false (0))
    extension = str(packet_vars['extension'])                                    #Extension - Disabled
    csi_count = str(format(packet_vars['csi_count'], 'b').zfill(4))              #Contributing Source Identifiers Count (Typically 0)
    byte1 = format(int((version + padding + extension + csi_count), 2), 'x').zfill(2)                           #Convert binary values to an int then format that as hex with 2 bytes of padding if requiredprint(byte1)

    #Generate second byte of header as binary string:
    marker = str(packet_vars['marker'])                                          #Marker (Typically false)
    payload_type = str(format(packet_vars['payload_type'], 'b').zfill(7))        #7 bit Payload Type (From https://tools.ietf.org/html/rfc3551#section-6)
    byte2 = format(int((marker + payload_type), 2), 'x').zfill(2)               #Convert binary values to an int then format that as hex with 2 bytes of padding if required

    sequence_number = format(packet_vars['sequence_number'], 'x').zfill(4)                               #16 bit sequence number (Starts from a random position and incriments per packet)
    
    timestamp = format(packet_vars['timestamp'], 'x').zfill(8)                   #(Typically incrimented by the fixed time between packets)
    
    ssrc = str(format(packet_vars['ssrc'], 'x').zfill(8))                        #SSRC 32 bits           (Typically randomly generated for each stream for uniqueness)

    payload = packet_vars['payload']

    packet = byte1 + byte2 + sequence_number + timestamp + ssrc + payload

    return packet
