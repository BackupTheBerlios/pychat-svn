# Copyright (c) 2005, Marcel van Rensburg and Neil Rutherford.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  1. Redistributions of source code must retain the above copyright notice,
#     this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
#  3. Neither the names of the copyright holders nor the names of the
#     contributors may be used to endorse or promote products derived from
#     this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNERS OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

# system imports
import socket

# SOAP imports
from SOAPpy import WSDL

class GoogleSearch:
    
    def __init__(self, proxy=None, key=None):
        """Default Constructor"""
        self.key = key
        self.proxy = proxy
        self.server = WSDL.Proxy('GoogleSearch.wsdl', http_proxy = self.proxy)

    def search(self, query, start=0, end=10, filter=False, restrict="", safeSearch=False):
        """Perform google search"""
        results = self.server.doGoogleSearch(self.key, query, start, end, filter, restrict, safeSearch, "", "utf-8", "utf-8")
        return GoogleSearchResults(results)

    def spell(self, word):
        """Get a spelling suggestion for a word"""
        results = self.server.doSpellingSuggestion(self.key, word)
        return results
                
    def setProxy(self, proxy):
        """Set the HTTP proxy that we must use to connect to Google"""
        self.proxy = proxy

    def getProxy(self):
        """Get the HTTP proxy that we must use to connect to Google"""
        return self.proxy

    def setLicense(self, key):
        """Set the Licence Key to be used for Google searches"""
        self.key = key

    def getLicense(self):
        """Get the Licence Key to be used for Google searches"""
        return self.key

class GoogleSearchResults:

    def __init__(self, results):
        """Default constructor"""
        self.results = results

    def getSearchTime(self):
        """Get Time taken to do search"""
        return self.results.searchTime

    def getTotalResults(self):
        """Get Estimated Total number of results"""
        return self.results.estimatedTotalResultsCount

    def getResultElements(self):
        """Get List of results"""
        return self.results.resultElements
