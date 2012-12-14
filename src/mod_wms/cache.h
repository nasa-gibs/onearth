// #define STRING_SIZE 2048

// One such record is stored for each page, in the indes file
// Zero-Zero means not present.
// These get stored in big endian order
typedef struct {
  long long offset;
  long long size;
} index_s;

typedef struct {
  int psizex,psizey; // page size in pixels
  int xcount,ycount; // page count on X and Y
  long long index_add; // Value to be added to the index record offset when
                       // reading and writing to the index file. This allows
                       // for index files to be shared between levels.
  index_s empty_record; // Default page pointer. Leave 0,0 if not used.

  // Bounding box for the level
  double X0, Y0, X1, Y1;

  // values for the pages size.
  double levelx,levely;

  char *dfname; // These are pointers or offsets
  char *ifname; //
} WMSlevel;

typedef struct {
  int size; // The size of the cache structure on disk.
            // It is equal to the size of the current structure+levels*sizeof(WMSlevel)
  int levels;  // How many levels are there
  int levelt_offset;
           // offset of the level structure table, from the cache itself
  int signature; // Content of the first four bytes of each page.
                 // Architecture independent. Set to 0 if not used.
  int orientation; // flag for page orientation. 0 is top-left, 1 is bottom-right
  int num_patterns; // num_patterns
  char *pattern; // patterns that cache matcheS
  char *prefix;
} WMSCache;

typedef struct { // One of these per cache pack
  int size; // Size of all records, plus the strings
  int count; // How many WMSCache records are there
} Caches;

// Macro to get the offset of the X-th cache giving the pointer to the cache file
#define GETCACHE(C,X) ((WMSCache *) ( ((char *) C) + sizeof(Caches) + X*sizeof(WMSCache) ))
// Macro to get a pointer to the level table of a given cache C, relative to the cache itself
#define GETLEVELS(C) ((WMSlevel *) ( ((char *) C) + C->levelt_offset ))
