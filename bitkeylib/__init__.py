try:
    import bitkey_pb2
except ImportError:
    print "bitkey_pb2.py not found. Please run /protobuf/build.sh to generate it!"
    import sys
    sys.exit()
