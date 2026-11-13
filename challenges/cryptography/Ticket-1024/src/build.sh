rm -f observation.fits static/errorLogs.zip
curl -L -X GET "https://mast.stsci.edu/search/hst/api/v0.1/retrieve_product?product_name=U2SA2902T%2Fu2sa2902t_flt.fits" --output "observation.fits" --fail --create-dirs
zip -0 -P 'N15c@D$YT8ASpc@7%0' static/errorLogs.zip observation.fits error.log