# Copyright REFITT Team 2019. All rights reserved.
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the Apache License (v2.0) as published by the Apache Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the Apache License for more details.
#
# You should have received a copy of the Apache License along with this program.
# If not, see <https://www.apache.org/licenses/LICENSE-2.0>.

"""
Refitt Services
===============

The refitt system includes a number of service daemons, some of them
independent, some of them intricately linked together in a sophisticated
network.

Exchange Services
-----------------
A strait forward, pure-python stream processing framework consisting of a
producer/consumer architecture supporting an arbitrary number of brokers and
topics. This service is depended on by all other refitt functions.

Cluster Services
----------------
Consisting of a primary cluster management server along with multiple other
auxiliary service daemons, the purpose of this service is to automatically
submit, monitor, and manage HPC batch jobs on a PBS-style computing cluster.

Database Services
-----------------
Multiple service daemons, including subsribers to the exchange service and
a REST-full web-api running on and exposing the data housed by the database
server.
"""
