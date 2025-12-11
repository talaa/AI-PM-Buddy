import React, { useEffect, useState } from "react";
import { ComposableMap, Geographies, Geography, Marker } from "react-simple-maps";
import { supabase } from "../lib/supabaseClient";

const geoUrl =
    "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

// Mapping of country names to [longitude, latitude]
const countryCoordinates = {
    "Egypt": [31.2357, 30.0444],
    "USA": [-95.7129, 37.0902],
    "United States": [-95.7129, 37.0902],
    "UK": [-3.4359, 55.3781],
    "United Kingdom": [-3.4359, 55.3781],
    "France": [2.2137, 46.2276],
    "Germany": [10.4515, 51.1657],
    "Canada": [-106.3468, 56.1304],
    "India": [78.9629, 20.5937],
    "China": [104.1954, 35.8617],
    "Japan": [138.2529, 36.2048],
    "Australia": [133.7751, -25.2744],
    "Brazil": [-51.9253, -14.2350],
    "UAE": [53.8478, 23.4241],
    "United Arab Emirates": [53.8478, 23.4241],
    "Saudi Arabia": [45.0792, 23.8859],
    "Italy": [12.5674, 41.8719],
    "Spain": [-3.7492, 40.4637],
    "Russia": [105.3188, 61.5240],
    "South Africa": [22.9375, -30.5595]
};

const WorldMap = () => {
    const [markers, setMarkers] = useState([]);

    useEffect(() => {
        fetchProjectLocations();
    }, []);

    const fetchProjectLocations = async () => {
        try {
            const { data: projects, error } = await supabase
                .from('projects')
                .select('country, project_name');

            if (error) throw error;

            // Group projects by country
            const countryGroups = {};
            projects.forEach(project => {
                const country = project.country?.trim();
                if (country) {
                    if (!countryGroups[country]) {
                        countryGroups[country] = { count: 0, names: [] };
                    }
                    countryGroups[country].count += 1;
                    countryGroups[country].names.push(project.project_name);
                }
            });

            // Convert groups to markers
            const newMarkers = Object.entries(countryGroups)
                .map(([country, data]) => {
                    const coordinates = countryCoordinates[country] || countryCoordinates[Object.keys(countryCoordinates).find(k => k.toLowerCase() === country.toLowerCase())];

                    if (coordinates) {
                        return {
                            name: country,
                            coordinates: coordinates,
                            count: data.count,
                            projectNames: data.names,
                            markerOffset: -15
                        };
                    }
                    return null;
                })
                .filter(Boolean);

            setMarkers(newMarkers);
        } catch (error) {
            console.error('Error fetching project locations:', error);
        }
    };

    return (
        <div className="glass-card p-6 h-full w-full flex flex-col">
            <h3 className="text-lg font-semibold">Project Locations</h3>
            <div className="flex-1 w-full h-full min-h-[400px]">
                <ComposableMap
                    projection="geoMercator"
                    projectionConfig={{
                        scale: 100,
                    }}
                    style={{ width: "100%", height: "100%" }}
                >
                    <Geographies geography={geoUrl}>
                        {({ geographies }) =>
                            geographies
                                .filter((geo) => geo.properties.name !== "Antarctica")
                                .map((geo) => (
                                    <Geography
                                        key={geo.rsmKey}
                                        geography={geo}
                                        fill="#EAEAEC"
                                        stroke="#D6D6DA"
                                        style={{
                                            default: { outline: "none" },
                                            hover: { fill: "#F53", outline: "none" },
                                            pressed: { outline: "none" },
                                        }}
                                    />
                                ))
                        }
                    </Geographies>
                    {markers.map(({ name, coordinates, markerOffset, count }) => (
                        <Marker key={name} coordinates={coordinates}>
                            <circle r={4 + (count * 2)} fill="#F53" stroke="#fff" strokeWidth={2} />
                            <text
                                textAnchor="middle"
                                y={markerOffset}
                                style={{ fontFamily: "system-ui", fill: "#5D5A6D", fontSize: "10px", fontWeight: "bold" }}
                            >
                                {name} ({count})
                            </text>
                        </Marker>
                    ))}
                </ComposableMap>
            </div>
        </div>
    );
};

export default WorldMap;
