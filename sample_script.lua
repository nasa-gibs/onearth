function handler( query_string, headers_in, notes )

   return [[{ "URL" : "]] .. query_string .. [[" }"]], 

          {
            ["Content-Type"] = "application/json" ;
	    ETag = "a1b2c3d4edge"
          },

          200
end
