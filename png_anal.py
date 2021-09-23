import sys
import io
import errno
import os
import png


def mkdirs(dir):

    try:
        os.makedirs(dir)

    except OSError as exception:
        if (exception.errno != errno.EEXIST):
            raise


def save_data_to_file(dest_dir, f_name, data):

    mkdirs(dest_dir)

    file_path = os.path.join(dest_dir, f_name)

    with io.open(file_path, 'wb') as f:
        f.write(data)


if len(sys.argv) != 2:
    print('Usage: '+ sys.argv[0] + ' png_file')
    sys.exit(0)

filename = sys.argv[1]

dest_dir = os.path.join(os.path.abspath(os.path.dirname(filename)),
                        'png_data')

with png.PNGFile() as pngfile:

    pngfile.open(filename, True)

    print('PNG file size       %d' % pngfile.png_file_size)

    ovl_size = 0
    if (pngfile.png_file_size < len(pngfile._file_data)):
        ovl_size = len(pngfile._file_data) - pngfile.png_file_size
        print('Overlay size:       %d' % ovl_size)
        save_data_to_file(dest_dir, 'ovl.bin',
                          pngfile._file_data[pngfile.png_file_size:])


    print('Width:              %d' % pngfile.width)
    print('Height:             %d' % pngfile.height)
    print('Bit depth:          %d' % pngfile.bit_depth)
    print('Colour type:        %d' % pngfile.color_type)
    print('Compression method: %d' % pngfile.compr_method)
    print('Filter method:      %d' % pngfile.filter_method)
    print('Interlace method:   %d' % pngfile.interlace_method)

    print('Chunks:             %d' % len(pngfile.chunks))

    print('Bits per pixel:     %d' % pngfile.bits_per_pixel)
    print('Pixels:             %d' % (pngfile.width * pngfile.height))
    print('Image size:         %d' % pngfile.image_data_size)

    for chunk_type in pngfile.chunks:

        try:
            chunk_name = chunk_type.decode()
        except UnicodeDecodeError:
            chunk_name = '%02X%02X%02X%02X' % (chunk_type[0],
                                               chunk_type[1],
                                               chunk_type[2],
                                               chunk_type[3])

        chunk_data = pngfile.chunks[chunk_type]
        save_data_to_file(dest_dir, chunk_name + '.bin', chunk_data)

    image_data = pngfile.extract_image_data()
    if (image_data is not None):
        print('Image data size     %d' % len(image_data))
        save_data_to_file(dest_dir, 'image_data.bin', image_data)

    profile = pngfile.extract_profile_data()
    if (profile is not None):
        print('ICC Profile name    \"%s\"' % profile[0])
        save_data_to_file(dest_dir, 'icc.bin', profile[1])
