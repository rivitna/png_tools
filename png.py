import io
import struct
import zlib


PNG_SIGN = b'\x89PNG\x0D\x0A\x1A\x0A'
PNG_SIGN_SIZE = 8

IHDR_CHUNK = b'IHDR'
IEND_CHUNK = b'IEND'
IDAT_CHUNK = b'IDAT'
ICCP_CHUNK = b'iCCP'

ICC_PROFILE_NAME_SIZE = 80
CHUNK_HDR_SIZE = 12


def read_dword(data, pos):

    val, = struct.unpack_from('>L', data, pos)
    return val


class PNGFormatError(Exception):
    """PNG format error exception."""

    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


class PNGFile(object):

    def __init__(self):

        self.close()


    def __enter__(self):

        self.close()
        return self


    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


    def close(self):

        self.width = None
        self.height = None
        self.bit_depth = None
        self.color_type = None
        self.compr_method = None
        self.filter_method = None
        self.interlace_method = None
        self.bits_per_pixel = None
        self.bytes_per_row = None
        self.image_data_size = None
        self.png_file_size = None
        self.chunks = None
        self._file_data = None
        self._ignore_crc = None
        self.is_corrupted = None


    def init(self, file_data, ignore_crc=False):

        self.is_corrupted = False
        self._file_data = file_data
        self._ignore_crc = ignore_crc

        sign = self._file_data[:PNG_SIGN_SIZE]
        if (sign != PNG_SIGN):
            raise PNGFormatError('Invalid PNG signature.')

        pos = PNG_SIGN_SIZE

        if (self._get_chunk_type(pos) != IHDR_CHUNK):
            raise PNGFormatError('Chunk IHDR is missing.')

        self.chunks = {}

        ihdr_data = self._read_chunk_data(pos)

        pos += CHUNK_HDR_SIZE + len(ihdr_data)

        self.chunks[IHDR_CHUNK] = ihdr_data

        self.width = read_dword(ihdr_data, 0)
        self.height = read_dword(ihdr_data, 4)
        self.bit_depth = ihdr_data[8]
        self.color_type = ihdr_data[9]
        self.compr_method = ihdr_data[10]
        self.filter_method = ihdr_data[11]
        self.interlace_method = ihdr_data[12]

        if (self.color_type == 0) or (self.color_type == 3):

            bit_depths = { 1, 2, 4, 8 }
            if (self.color_type == 0):
                bit_depths.add(16)
            pixel_samples = 1

        elif ((self.color_type == 2) or
              (self.color_type == 4) or
              (self.color_type == 6)):

            bit_depths = { 8, 16 }
            pixel_samples = 2
            if (self.color_type == 2):
                pixel_samples = 3
            elif (self.color_type == 6):
                pixel_samples = 4

        else:
            raise PNGFormatError('Invalid colour type.')

        if (self.compr_method != 0):
            raise PNGFormatError('Invalid compression method.')

        if (self.bit_depth not in bit_depths):
            raise PNGFormatError('Invalid bit depth.')

        if (self.filter_method != 0):
            raise PNGFormatError('Invalid filter method.')

        if (self.interlace_method & (~1)):
            raise PNGFormatError('Invalid interlace method.')

        self.bits_per_pixel = pixel_samples * self.bit_depth
        self.bytes_per_row = (self.width * self.bits_per_pixel + 7) // 8 + 1
        self.image_data_size = self.bytes_per_row * self.height

        idat_data = None

        while True:

            chunk_type = self._get_chunk_type(pos)

            chunk_data = self._read_chunk_data(pos)

            if (chunk_type == IDAT_CHUNK):
                if (idat_data is None):
                    idat_data = chunk_data
                else:
                    idat_data += chunk_data
            else:
                self.chunks[chunk_type] = chunk_data

            pos += CHUNK_HDR_SIZE + len(chunk_data)

            if (chunk_type == IEND_CHUNK):
                break

        if (idat_data is not None):
            self.chunks[IDAT_CHUNK] = idat_data

        self.png_file_size = pos


    def open(self, file_name, ignore_crc=False):

        with io.open(file_name, 'rb') as f:
            self.init(f.read(), ignore_crc)


    def extract_image_data(self):

        idat_data = self.chunks.get(IDAT_CHUNK)
        if (idat_data is None):
            return None

        return zlib.decompress(idat_data)


    def extract_profile_data(self):

        iccp_data = self.chunks.get(ICCP_CHUNK)
        if (iccp_data is None):
            return None

        i = iccp_data.find(0)
        if (i < 0) or (i >= ICC_PROFILE_NAME_SIZE):
            return None

        profile_name = iccp_data[:i].decode('Latin-1')

        compr_method = iccp_data[i + 1]
        if (compr_method != 0):
            raise PNGFormatError('Compression method not supported.')

        profile_data = zlib.decompress(iccp_data[i + 2:])

        return profile_name, profile_data


    def _get_chunk_type(self, pos):

        return self._read_data(pos + 4, 4)


    def _get_chunk_size(self, pos):

        return self._read_dword(pos)


    def _read_chunk_data(self, pos):

        chunk_size = self._get_chunk_size(pos)

        chunk_type = self._get_chunk_type(pos)

        crc = zlib.crc32(chunk_type)

        chunk_data = b''
        if (chunk_size != 0):
            chunk_data = self._read_data(pos + 8, chunk_size)
            crc = zlib.crc32(chunk_data, crc)

        chunk_crc = self._read_dword(pos + 8 + chunk_size)
       
        if (crc != chunk_crc):
            self.is_corrupted = True
            if not self._ignore_crc:
                raise PNGFormatError('Invalid chunk data CRC32.')

        return chunk_data


    def _read_data(self, pos, size):

        return self._file_data[pos : pos + size]


    def _read_dword(self, pos):

        return read_dword(self._file_data, pos)
