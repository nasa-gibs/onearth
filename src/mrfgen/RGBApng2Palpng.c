/*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You may obtain a copy of the License at
*
* http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
*/

/*
  gcc -O3 RGBApng2Palpng.c -o RGBApng2Palpng -lpng

  NOTE: this currently only outputs a palette PNG.
*/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <png.h>

/* from gif.h */
typedef unsigned char byte;

/* from hdf.h */
#define FALSE 0
#define TRUE (!FALSE)

#define MAXNAMELENGTH 200

/* Face it, if more than 100 image colors are not the the color table you've obviously got the wrong table! */
#define MAX_NOT_FOUND 100

/* Fixes PNG issue with libpng > 1.4 */
#define png_infopp_NULL (png_infopp)NULL
#define int_p_NULL (int*)NULL

enum {COLOR, GRAYSCALE};


int main(int argc, char *argv[])
{
char filename1[MAXNAMELENGTH], filename2[MAXNAMELENGTH];
int idx, k, j;
FILE *fd, *lut=NULL;
byte *imgarr;
int userfill=-1;
int colorstyle=GRAYSCALE;
int red, green, blue, alpha;
int redarr[256], greenarr[256], bluearr[256], alphaarr[256];
unsigned char lutname[MAXNAMELENGTH];
unsigned char verbose=FALSE;

png_structp png_ptr;
png_infop info_ptr;
png_colorp png_palette;
png_colorp dest_pal;
unsigned char *png_trans;

png_structp in_png_ptr;
png_infop in_info_ptr;
png_uint_32 width, height;
int bit_depth, color_type, interlace_type;
FILE *fp;

png_uint_32  i, rowbytes;
byte  *image_data = NULL;
png_bytepp  row_pointers = NULL;
int bytesperpixel;
int found;

int num_not_found=0;
int rednotfound[MAX_NOT_FOUND], greennotfound[MAX_NOT_FOUND], bluenotfound[MAX_NOT_FOUND];
int return_code=0;

  filename1[0] = '\0';
  filename2[0] = '\0';
  lutname[0] = '\0';

  if (argc < 2) {
    fprintf(stderr, "Usage: RGBApng2Palpng [-v] -lut=<ColorMap file (must contain RGBA)> -fill=<LUT index value> -of=<output palette PNG file> <input RGBA PNG file>\n");
    exit(-1);
  }

  for (j=1; j<argc; j++)
    if ( strcmp(argv[j], "-v") == 0 ) {
      fprintf(stderr, "Verbose mode requested.\n");
      verbose = TRUE;
    }

  for (j=1; j<argc; j++) {
    if (strstr(argv[j], "-of=") == argv[j] ) {
        if ( sscanf(argv[j], "-of=%s", filename2) != 1 ) {
          fprintf(stderr, "Cannot read output file\n");
          exit(-1);
        }
        if (verbose)
          fprintf(stderr, "Output file: %s\n", filename2);
    } else if (strstr(argv[j], "-lut=") == argv[j] ) {
        if ( sscanf(argv[j], "-lut=%s", lutname) != 1 ) {
          fprintf(stderr, "Cannot parse LUT name\n");
          exit(-1);
        }
        if (verbose)
          fprintf(stderr, "Color LUT: %s\n", lutname);
        colorstyle = COLOR;
    } else if (strstr(argv[j], "-fill=") == argv[j] ) {
        if (sscanf(argv[j], "-fill=%d", &userfill) != 1) {
          fprintf(stderr, "Cannot read user fill value\n");
          exit(-1);
        }
        if ( userfill < 0 || userfill > 255 ) {
          fprintf(stderr, "User fill value must be between 0 and 255\n");
          exit(-1);
        }
        if (verbose)
          fprintf(stderr, "User fill value: %d\n", userfill);
    } else if ( strlen(filename2) == 0 &&
                strcmp(argv[j], "-") == 0 ) {
        strcpy(filename2, "stdout");
        if (verbose)
          fprintf(stderr, "Output file: %s\n", filename2);
    } else if ( strcmp(argv[j], "-v") != 0 ) {
        strcpy(filename1, argv[j]);
        if (verbose)
          fprintf(stderr, "Input file: %s\n", filename1);
    }
  }

  if ( strlen(filename1) == 0  ||
       strlen(filename2) == 0  ||
       strlen(lutname) == 0  ||
       userfill < 0 ) {
    fprintf(stderr, "Unable to get all arguments\n");
    exit(-1);
  }

  if ((fp = fopen(filename1, "rb")) == NULL) {
    fprintf(stderr, "Unable to open input file: %s\n", filename1);
    exit(-1);
  }

  in_png_ptr = png_create_read_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);

  if (in_png_ptr == NULL) {
    fclose(fp);
    fprintf(stderr, "Could not allocate PNG read struct\n");
    return (-1);
  }

  in_info_ptr = png_create_info_struct(in_png_ptr);
  if (in_info_ptr == NULL) {
    fclose(fp);
    png_destroy_read_struct(&in_png_ptr, png_infopp_NULL, png_infopp_NULL);
    fprintf(stderr, "Could not allocate input PNG info struct\n");
    return (-1);
  }

  if (setjmp(png_jmpbuf(in_png_ptr))) {
    /* Free all of the memory associated with the png_ptr and info_ptr */
    png_destroy_read_struct(&in_png_ptr, &in_info_ptr, png_infopp_NULL);
    fclose(fp);
    /* If we get here, we had a problem reading the file */
    return (-1);
  }

  /* Set up the input control if you are using standard C streams */
  png_init_io(in_png_ptr, fp);

  png_read_info(in_png_ptr, in_info_ptr);

  png_get_IHDR(in_png_ptr, in_info_ptr, &width, &height, &bit_depth, &color_type,
       &interlace_type, int_p_NULL, int_p_NULL);

  if (verbose) {
    fprintf(stderr, "Width: %d\n", width);
    fprintf(stderr, "Height: %d\n", height);
    fprintf(stderr, "Bit Depth: %d\n", bit_depth);
    switch(color_type) {
          case 0:
            fprintf(stderr, "Color Type: Gray (0)\n");
            break;
          case 3:
            fprintf(stderr, "Color Type: Palette (3)\n");
            break;
          case 2:
            fprintf(stderr, "Color Type: RGB (2)\n");
            break;
          case 6:
            fprintf(stderr, "Color Type: RGB Alpha (6)\n");
            break;
          case 4:
            fprintf(stderr, "Color Type: Gray Alpha (4)\n");
            break;
          default:
            fprintf(stderr, "Unknown Color Type: %d\n", color_type);
    }
    switch(interlace_type) {
          case 0:
            fprintf(stderr, "Interlace Type: None (0)\n");
            break;
          case 1:
            fprintf(stderr, "Interlace Type: Adam7 (1)\n");
            break;
          default:
            fprintf(stderr, "Unknown Interlace Type: %d\n", interlace_type);
    }
  }

  rowbytes = png_get_rowbytes(in_png_ptr, in_info_ptr);

  if ( verbose ) fprintf(stderr, "Number of bytes per row: %d\n", rowbytes);

  if ((image_data = (byte *)malloc(rowbytes*height)) == NULL) {
    png_destroy_read_struct(&in_png_ptr, &in_info_ptr, NULL);
    exit(-1);
  }

  if ((row_pointers = (png_bytepp)malloc(height*sizeof(png_bytep))) == NULL) {
    png_destroy_read_struct(&in_png_ptr, &in_info_ptr, NULL);
    free(image_data);
    image_data = NULL;
    exit(-1);
  }

  for (i = 0;  i < height;  ++i)
    row_pointers[i] = image_data + i*rowbytes;

  /* now we can go ahead and just read the whole image */

  png_read_image(in_png_ptr, row_pointers);

  imgarr = (byte *) malloc(height * width * sizeof(byte));

  png_palette = (png_colorp)malloc( 256 * sizeof( png_color) );
  dest_pal = png_palette;
  if (colorstyle == GRAYSCALE)
    for (j=0; j<256; j++) {
      dest_pal->red = dest_pal->green = dest_pal->blue = j;
      dest_pal++;
      
      redarr[j] = greenarr[j] = bluearr[j] = j;
      alphaarr[j] = 255;
  } else {
    if ( (lut = fopen(lutname, "r")) != NULL ) {
    	if (strlen(lutname) > 4 && ((!strcmp(lutname + strlen(lutname) - 4, ".xml")))) {
    		fprintf(stderr, "Opening colormap file %s\n", lutname);

    		if (lut) {
    			int size = 1024, pos;
    			int c;
    			int j = 0;
    			char *buffer = (char *)malloc(size);
    			const char *entry_key = "ColorMapEntry";
    			const char *rgb_key = "rgb=";
    			const char *transparent_str = "transparent=\"true\"";
    			
    			do { // read all lines in file
					pos = 0;
					do { // read one line
					c = fgetc(lut);
					if(c != EOF) buffer[pos++] = (char)c;
						if(pos >= size - 1) { // increase buffer length - leave room for 0
							size *=2;
							buffer = (char*)realloc(buffer, size);
						}
					} while(c != EOF && c != '\n');
					buffer[pos] = 0;

					char *entry = strstr(buffer,entry_key);
					char *rgb = strstr(buffer,rgb_key);
					
					// GIBS colormap RGB values
					if (rgb != NULL && entry != NULL) {
	        			char rgb_string[15];
						int rgb_length = strlen(rgb);
						int rgb_pos = pos - rgb_length;
						memcpy(rgb_string, &buffer[rgb_pos+5], 15);
						rgb_string[15] = '\0';
						// break rgb string into int values
						int rgb_array[3];
						int i = 0;
						char *rgb_values = strtok(rgb_string, ",");
						while (rgb_values != NULL) {
							rgb_array[i++] = strtol(rgb_values,NULL,10);
							rgb_values = strtok(NULL, ",");
						}
						red = rgb_array[0]; green = rgb_array[1]; blue = rgb_array[2];
						dest_pal->red = red;
						dest_pal->green = green;
						dest_pal->blue = blue;

						alpha = strstr(entry, transparent_str) != NULL ? 0 : 255;
						
						dest_pal++;
						redarr[j] = red;
						greenarr[j] = green;
						bluearr[j] = blue;
						alphaarr[j] = alpha;
						if ( verbose ) fprintf(stderr, "RGBA: %d %d %d %d \n", redarr[j], greenarr[j] , bluearr[j], alphaarr[j]);
						j++;
					}
    			} while(c != EOF);;
    		    fclose(lut);
    		    free(buffer);

    			// fill in palette with 0,0,0,0 values
    			for (; j<256; j++) {
                    dest_pal->red = dest_pal->green = dest_pal->blue = 0;
                    dest_pal++;  // Not sure  if this is needed

                    redarr[j] = greenarr[j] = bluearr[j] = alphaarr[j] = 0;

                    if ( verbose ) fprintf(stderr, "RGBA: %d %d %d %d \n", redarr[j], greenarr[j] , bluearr[j], alphaarr[j]);
    			}
    		}
    	} else {
			for (j=0; j<256; j++)
			  if ( fscanf(lut, "%d %d %d %d", &red, &green, &blue, &alpha) != 4 ) {
				  fprintf(stderr, "Cannot read color index %d in LUT file\n", j);
				  exit(-1);
			  } else {
				  dest_pal->red = red;
				  dest_pal->green = green;
				  dest_pal->blue = blue;
				  dest_pal++;
				  
				  redarr[j] = red;
				  greenarr[j] = green;
				  bluearr[j] = blue;
				  alphaarr[j] = alpha;
			  }
			fclose(lut);
    	}
    } else {
        fprintf(stderr, "Cannot open LUT file %s.\n", lutname);
        exit(-1);
    }
  }

  png_trans = (unsigned char *)malloc(256 * sizeof(unsigned char));
  for (j=0; j<256; j++) {
    png_trans[j] = alphaarr[j];
  }

  switch(color_type) {
    case(PNG_COLOR_TYPE_GRAY): bytesperpixel = 1;
                               break;
    case(PNG_COLOR_TYPE_PALETTE): bytesperpixel = 1;
                               break;
    case(PNG_COLOR_TYPE_RGB): bytesperpixel = 3;
                               break;
    case(PNG_COLOR_TYPE_RGB_ALPHA): bytesperpixel = 4;
                               break;
    case(PNG_COLOR_TYPE_GRAY_ALPHA): bytesperpixel = 2;
                               break;
    default:
            fprintf(stderr, "Unknown Color Type: %d\n", color_type);
            exit(-1);
  }

  if ( color_type != PNG_COLOR_TYPE_RGB && color_type != PNG_COLOR_TYPE_RGB_ALPHA ) {
    fprintf(stderr, "Color Type must be RGB or RGBA.\n");
    exit(-1);
  }
  
  if ( verbose ) fprintf(stderr, "Bytes per Pixel: %d\n", bytesperpixel);

  for (i = 0;  i < height;  i++) {
    for (j = 0;  j < width;  j++) {

      idx = i*width+j;
      red = image_data[i*width*bytesperpixel+j*bytesperpixel];
      green = image_data[i*width*bytesperpixel+j*bytesperpixel+1];
      blue = image_data[i*width*bytesperpixel+j*bytesperpixel+2];
  
      found = FALSE;
      for (k = 0;  k < 256;  k++) {

        if ( red == redarr[k] &&
             green == greenarr[k] &&
             blue == bluearr[k] ) {
              imgarr[idx] = (unsigned char) k;
              found = TRUE;
              break;
        }
      }
      if ( !found ) {
        imgarr[idx] = (unsigned char) userfill;
        found = FALSE;
        if ( num_not_found < MAX_NOT_FOUND ) {
          for (k = 0; k < num_not_found; k++) {
            if ( red == rednotfound[k] &&
                 green == greennotfound[k] &&
                 blue == bluenotfound[k] ) {
              found = TRUE;
              break;
            }
          }
          if ( !found ) {
            rednotfound[num_not_found] = red;
            greennotfound[num_not_found] = green;
            bluenotfound[num_not_found] = blue;
            num_not_found++;
          }
        }
      }
    }
  }

  if ( num_not_found > 0 ) {
    return_code = num_not_found;
    fprintf(stderr, "%d Colors in image not found in color table\n", num_not_found);
    for (k = 0; k < num_not_found; k++) {
      fprintf(stderr, "%3d %3d %3d\n", rednotfound[k], greennotfound[k], bluenotfound[k]);
    }
  }

  // Done with the read, clean up
  free(row_pointers);
  row_pointers = NULL;

  png_read_end(in_png_ptr, NULL);
  
  free(image_data);
  image_data = NULL;

  fclose(fp);

  // Start the write

  if (strcmp(filename2, "stdout") == 0)
    fd = stdout;
  else if ( (fd = fopen(filename2, "wb")) == NULL ) {
    fprintf(stderr, "Cannot open file %s.\n", filename2);
    exit(-1);
  }

  // Initialize write structure
  png_ptr = png_create_write_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
  if (png_ptr == NULL) {
    fprintf(stderr, "Could not allocate PNG write struct\n");
    exit(-1);
  }

  // Initialize info structure
  info_ptr = png_create_info_struct(png_ptr);
  if (info_ptr == NULL) {
    fprintf(stderr, "Could not allocate PNG info struct\n");
    exit(-1);
  }

  if (setjmp(png_jmpbuf(png_ptr))) {
    fprintf(stderr, "Error during PNG init_io\n");
    exit(-1);
  }

  png_init_io(png_ptr, fd);

  if (setjmp(png_jmpbuf(png_ptr))) {
    fprintf(stderr, "Error during PNG set header\n");
    exit(-1);
  }

  // Write header (8 bit colour depth)
  png_set_IHDR(png_ptr, info_ptr, width, height,
         8, PNG_COLOR_TYPE_PALETTE, PNG_INTERLACE_NONE,
         PNG_COMPRESSION_TYPE_BASE, PNG_FILTER_TYPE_BASE);

  if (setjmp(png_jmpbuf(png_ptr))) {
    fprintf(stderr, "Error during PNG set pallette\n");
    exit(-1);
  }

  png_set_PLTE(png_ptr, info_ptr, png_palette, 256);

  if (setjmp(png_jmpbuf(png_ptr))) {
    fprintf(stderr, "Error during PNG set transparency\n");
    exit(-1);
  }

  png_set_tRNS(png_ptr, info_ptr, png_trans, 256, NULL);

  if (setjmp(png_jmpbuf(png_ptr))) {
    fprintf(stderr, "Error during PNG write info\n");
    exit(-1);
  }

  png_write_info(png_ptr, info_ptr);

  if (setjmp(png_jmpbuf(png_ptr))) {
    fprintf(stderr, "Error during PNG write row\n");
    exit(-1);
  }

  for (k=0; k<height; k++) {
    idx = k * width;
    png_write_row(png_ptr, &imgarr[idx]);
  }

  if (setjmp(png_jmpbuf(png_ptr))) {
    fprintf(stderr, "Error during PNG write end\n");
    exit(-1);
  }

  // End write
  png_write_end(png_ptr, NULL);

  fclose(fd);
  free(imgarr);
  free(png_palette);
  free(png_trans);

  if (info_ptr != NULL) png_free_data(png_ptr, info_ptr, PNG_FREE_ALL, -1);
  if (png_ptr != NULL) png_destroy_write_struct(&png_ptr, (png_infopp)NULL);

  return return_code;

}
