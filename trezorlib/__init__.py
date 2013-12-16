try:
    import messages_pb2 as proto
except ImportError:
    print "Source messages_pb2.py or types_pb2.py not found. Make sure python-protobuf is installed and run build_pb.sh to generate it."
    import sys
    sys.exit()
