try:
    import trezor_pb2 as proto
except ImportError:
    print "Source trezor_pb2.py not found. Make sure python-protobuf is installed and run build_pb.sh to generate it."
    import sys
    sys.exit()
