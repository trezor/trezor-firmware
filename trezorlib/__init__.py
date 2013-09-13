try:
    import trezor_pb2 as proto
except ImportError:
    print "trezor_pb2.py not found. Please run /protobuf/build.sh to generate it!"
    import sys
    sys.exit()
