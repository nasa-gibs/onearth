1. Installation
   sudo yum install gcc -y

   python3 -m pip install --upgrade cython
   sudo yum install python3-devel -y

   pip3 install Pillow==8.1.0
   pip3 install numpy
   python3 setup.py build_ext --inplace

3. Run
   python3 RgbPngToPalPng.py -v -c MODIS_Brightness_Temp_Band31.xml -i rgba.png -o pal.png -f 0
