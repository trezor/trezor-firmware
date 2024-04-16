## Memory usage comparison

## Legacy solution

**Memory with DMA access**

```
buffer_line_16bpp              @.buf        1440
buffer_line_4bpp               @.buf         360
buffer_text                    @.buf        4320
-------------------------------------------------
                                            6120
```

**Memory without DMA access**

```
buffer_jpeg                    @.no_dma     7680
buffer_jpeg_work               @.no_dma    10500
buffer_blurring                @.no_dma    14400
buffer_blurring_totals         @.no_dma     1440
zlib context+window            @.stack      2308
-------------------------------------------------
                                           36328
```

## New drawing library

The memory usage is configurable, so the two options are considered.\

MIN variant is slower, but consumes less memory. OPT variant should
be sufficient for all purposes.


**Memory with DMA access**

```
                                            MIN      OPT
ProgressiveRenderer.slice      @.buf        480     7680
ProgressiveRenderer.scratch    @.buf        480     2048
---------------------------------------------------------
                                            960     9728
```

**Memory without DMA access**

```
ProgressiveRenderer.list       @.stack      512     2048
zlib decompression context     @.no_dma    2308     6924
jpeg decompressor              @.no_dma   10500    10500
partial jpeg image             @.no_dma    7680     7680
blurring window/totals         @.no_dma    7920     7920
------------------------------------------------------------------
                                          28920    35072
```



