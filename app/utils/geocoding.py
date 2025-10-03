import logging
from typing import Optional, Dict
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time

logger = logging.getLogger(__name__)


class GeocodingService:
    """Service for reverse geocoding coordinates to location names"""

    def __init__(self):
        # Initialize Nominatim geocoder (OpenStreetMap)
        # Use a descriptive user_agent for your application
        self.geolocator = Nominatim(
            user_agent="coral-bleaching-monitor/1.0", timeout=10
        )
        self._cache = {}  # Simple in-memory cache

    def get_location_name(
        self, latitude: float, longitude: float, language: str = "en"
    ) -> str:
        """
        Get location name from coordinates using reverse geocoding

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            language: Language for location name (default: English)

        Returns:
            Formatted location name or coordinate fallback
        """
        # Create cache key
        cache_key = f"{round(latitude, 4)},{round(longitude, 4)}"

        # Check cache first
        if cache_key in self._cache:
            logger.info(f"Geocoding: Using cached location for {cache_key}")
            return self._cache[cache_key]

        try:
            # Add small delay to respect rate limits (1 request per second for Nominatim)
            time.sleep(1)

            # Perform reverse geocoding
            location = self.geolocator.reverse(
                f"{latitude}, {longitude}", language=language, exactly_one=True
            )

            if location and location.raw:
                # Extract meaningful location information
                address = location.raw.get("address", {})
                location_name = self._format_location_name(address, latitude, longitude)

                # Cache the result
                self._cache[cache_key] = location_name
                logger.info(
                    f"Geocoding: Found location '{location_name}' for ({latitude}, {longitude})"
                )

                return location_name
            else:
                # Fallback to coordinates
                fallback = f"Location ({round(latitude, 4)}, {round(longitude, 4)})"
                self._cache[cache_key] = fallback
                return fallback

        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.warning(f"Geocoding service error: {str(e)}")
            return f"Location ({round(latitude, 4)}, {round(longitude, 4)})"
        except Exception as e:
            logger.error(f"Geocoding error: {str(e)}")
            return f"Location ({round(latitude, 4)}, {round(longitude, 4)})"

    def _format_location_name(
        self, address: Dict, latitude: float, longitude: float
    ) -> str:
        """
        Format location name from address components
        Priority: city/town > county/municipality > state/region > country
        """
        # Try to get the most specific location
        components = []

        # Check for city/town/village
        city = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
            or address.get("suburb")
        )

        if city:
            components.append(city)

        # Add county or province if available and different from city
        county = address.get("county") or address.get("province")
        if county and county != city:
            components.append(county)

        # Add state/region
        state = (
            address.get("state")
            or address.get("region")
            or address.get("state_district")
        )
        if state and len(components) < 2:
            components.append(state)

        # Always add country
        country = address.get("country")
        if country:
            components.append(country)

        # If we have components, join them
        if components:
            # Limit to 3 components for brevity
            location_name = ", ".join(components[:3])
            return location_name

        # Fallback to coordinates
        return f"Location ({round(latitude, 4)}, {round(longitude, 4)})"

    def get_detailed_location_info(
        self, latitude: float, longitude: float
    ) -> Optional[Dict]:
        """
        Get detailed location information

        Returns:
            Dictionary with detailed address components or None
        """
        try:
            time.sleep(1)  # Rate limiting

            location = self.geolocator.reverse(
                f"{latitude}, {longitude}", exactly_one=True
            )

            if location and location.raw:
                return {
                    "display_name": location.address,
                    "address": location.raw.get("address", {}),
                    "latitude": latitude,
                    "longitude": longitude,
                }

            return None

        except Exception as e:
            logger.error(f"Error getting detailed location info: {str(e)}")
            return None


# Create singleton instance
geocoding_service = GeocodingService()
