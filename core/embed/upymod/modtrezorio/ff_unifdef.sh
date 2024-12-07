unifdef \
    -DFF_FS_READONLY=0 \
    -DFF_FS_MINIMIZE=0 \
    -DFF_USE_STRFUNC=0 \
    -DFF_USE_FIND=0 \
    -DFF_USE_FASTSEEK=0 \
    -DFF_USE_EXPAND=0 \
    -DFF_USE_CHMOD=0 \
    -DFF_USE_LABEL=1 \
    -DFF_USE_FORWARD=0 \
    -DFF_CODE_PAGE=437 \
    -DFF_USE_LFN=1 \
    -DFF_LFN_UNICODE=2 \
    -DFF_STRF_ENCODE=3 \
    -DFF_FS_RPATH=0 \
    -DFF_VOLUMES=1 \
    -DFF_STR_VOLUME_ID=0 \
    -DFF_MULTI_PARTITION=0 \
    -DFF_USE_TRIM=0 \
    -DFF_FS_NOFSINFO=0 \
    -DFF_FS_TINY=0 \
    -DFF_FS_EXFAT=0 \
    -DFF_FS_NORTC=1 \
    -DFF_FS_LOCK=0 \
    -DFF_FS_REENTRANT=0 \
    -DFF_LBA64=0 \
    -DFF_MULTI_PARTITION=0 \
    ff.c -o ff.c

unifdef \
    -DFF_CODE_PAGE=437 \
    ffunicode.c -o ffunicode.c
