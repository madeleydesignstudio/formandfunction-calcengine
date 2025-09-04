"""
gRPC client for communicating with the Form & Function Go API
"""
import grpc
import logging
from typing import List, Optional, Dict, Any
from proto import steelbeam_pb2
from proto import steelbeam_pb2_grpc

logger = logging.getLogger(__name__)

class SteelBeamGRPCClient:
    """gRPC client for steel beam service"""

    def __init__(self, server_address: str = "localhost:9090"):
        """
        Initialize the gRPC client

        Args:
            server_address: Address of the gRPC server (host:port)
        """
        self.server_address = server_address
        self.channel = None
        self.stub = None

    def connect(self):
        """Establish connection to the gRPC server"""
        try:
            self.channel = grpc.insecure_channel(self.server_address)
            self.stub = steelbeam_pb2_grpc.SteelBeamServiceStub(self.channel)
            logger.info(f"Connected to gRPC server at {self.server_address}")
        except Exception as e:
            logger.error(f"Failed to connect to gRPC server: {e}")
            raise

    def disconnect(self):
        """Close the gRPC channel"""
        if self.channel:
            self.channel.close()
            logger.info("Disconnected from gRPC server")

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()

    def get_all_beams(self) -> List[Dict[str, Any]]:
        """
        Get all steel beams from the API

        Returns:
            List of steel beam dictionaries
        """
        if not self.stub:
            raise RuntimeError("Not connected to gRPC server. Call connect() first.")

        try:
            request = steelbeam_pb2.GetBeamsRequest()
            response = self.stub.GetBeams(request)

            beams = []
            for beam in response.beams:
                beams.append(self._proto_beam_to_dict(beam))

            logger.info(f"Retrieved {len(beams)} beams via gRPC")
            return beams

        except grpc.RpcError as e:
            logger.error(f"gRPC error getting beams: {e}")
            raise

    def get_beam(self, section_designation: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific steel beam by section designation

        Args:
            section_designation: Section designation of the beam

        Returns:
            Steel beam dictionary or None if not found
        """
        if not self.stub:
            raise RuntimeError("Not connected to gRPC server. Call connect() first.")

        try:
            request = steelbeam_pb2.GetBeamRequest(section_designation=section_designation)
            response = self.stub.GetBeam(request)

            if response.found:
                beam_dict = self._proto_beam_to_dict(response.beam)
                logger.info(f"Retrieved beam {section_designation} via gRPC")
                return beam_dict
            else:
                logger.warning(f"Beam {section_designation} not found")
                return None

        except grpc.RpcError as e:
            logger.error(f"gRPC error getting beam {section_designation}: {e}")
            raise

    def create_beam(self, beam_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new steel beam

        Args:
            beam_data: Dictionary containing beam properties

        Returns:
            Created beam dictionary
        """
        if not self.stub:
            raise RuntimeError("Not connected to gRPC server. Call connect() first.")

        try:
            proto_beam = self._dict_to_proto_beam(beam_data)
            request = steelbeam_pb2.CreateBeamRequest(beam=proto_beam)
            response = self.stub.CreateBeam(request)

            if response.success:
                created_beam = self._proto_beam_to_dict(response.beam)
                logger.info(f"Created beam {beam_data.get('section_designation')} via gRPC")
                return created_beam
            else:
                raise RuntimeError(f"Failed to create beam: {response.message}")

        except grpc.RpcError as e:
            logger.error(f"gRPC error creating beam: {e}")
            raise

    def get_stock_status(self, product_id: str, postcode: str) -> Dict[str, Any]:
        """
        Get stock status for a product

        Args:
            product_id: Product ID
            postcode: Postcode

        Returns:
            Stock status information
        """
        if not self.stub:
            raise RuntimeError("Not connected to gRPC server. Call connect() first.")

        try:
            request = steelbeam_pb2.GetStockStatusRequest(
                product_id=product_id,
                postcode=postcode
            )
            response = self.stub.GetStockStatus(request)

            result = {
                'product_id': response.product_id,
                'postcode': response.postcode,
                'status': response.status,
                'success': response.success,
                'message': response.message
            }

            logger.info(f"Retrieved stock status for {product_id} via gRPC")
            return result

        except grpc.RpcError as e:
            logger.error(f"gRPC error getting stock status: {e}")
            raise

    def _proto_beam_to_dict(self, proto_beam) -> Dict[str, Any]:
        """Convert protobuf SteelBeam to dictionary"""
        return {
            'section_designation': proto_beam.section_designation,
            'mass_per_metre': proto_beam.mass_per_metre,
            'depth_of_section': proto_beam.depth_of_section,
            'width_of_section': proto_beam.width_of_section,
            'thickness_web': proto_beam.thickness_web,
            'thickness_flange': proto_beam.thickness_flange,
            'root_radius': proto_beam.root_radius,
            'depth_between_fillets': proto_beam.depth_between_fillets,
            'ratios_for_local_buckling_web': proto_beam.ratios_for_local_buckling_web,
            'ratios_for_local_buckling_flange': proto_beam.ratios_for_local_buckling_flange,
            'end_clearance': proto_beam.end_clearance,
            'notch': proto_beam.notch,
            'dimensions_for_detailing_n': proto_beam.dimensions_for_detailing_n,
            'surface_area_per_metre': proto_beam.surface_area_per_metre,
            'surface_area_per_tonne': proto_beam.surface_area_per_tonne,
            'second_moment_of_area_axis_y': proto_beam.second_moment_of_area_axis_y,
            'second_moment_of_area_axis_z': proto_beam.second_moment_of_area_axis_z,
            'radius_of_gyration_axis_y': proto_beam.radius_of_gyration_axis_y,
            'radius_of_gyration_axis_z': proto_beam.radius_of_gyration_axis_z,
            'elastic_modulus_axis_y': proto_beam.elastic_modulus_axis_y,
            'elastic_modulus_axis_z': proto_beam.elastic_modulus_axis_z,
            'plastic_modulus_axis_y': proto_beam.plastic_modulus_axis_y,
            'plastic_modulus_axis_z': proto_beam.plastic_modulus_axis_z,
            'buckling_parameter': proto_beam.buckling_parameter,
            'torsional_index': proto_beam.torsional_index,
            'warping_constant': proto_beam.warping_constant,
            'torsional_constant': proto_beam.torsional_constant,
            'area_of_section': proto_beam.area_of_section,
        }

    def _dict_to_proto_beam(self, beam_dict: Dict[str, Any]):
        """Convert dictionary to protobuf SteelBeam"""
        return steelbeam_pb2.SteelBeam(
            section_designation=beam_dict.get('section_designation', ''),
            mass_per_metre=beam_dict.get('mass_per_metre', 0.0),
            depth_of_section=beam_dict.get('depth_of_section', 0.0),
            width_of_section=beam_dict.get('width_of_section', 0.0),
            thickness_web=beam_dict.get('thickness_web', 0.0),
            thickness_flange=beam_dict.get('thickness_flange', 0.0),
            root_radius=beam_dict.get('root_radius', 0.0),
            depth_between_fillets=beam_dict.get('depth_between_fillets', 0.0),
            ratios_for_local_buckling_web=beam_dict.get('ratios_for_local_buckling_web', 0.0),
            ratios_for_local_buckling_flange=beam_dict.get('ratios_for_local_buckling_flange', 0.0),
            end_clearance=beam_dict.get('end_clearance', 0.0),
            notch=beam_dict.get('notch', 0.0),
            dimensions_for_detailing_n=beam_dict.get('dimensions_for_detailing_n', 0.0),
            surface_area_per_metre=beam_dict.get('surface_area_per_metre', 0.0),
            surface_area_per_tonne=beam_dict.get('surface_area_per_tonne', 0.0),
            second_moment_of_area_axis_y=beam_dict.get('second_moment_of_area_axis_y', 0.0),
            second_moment_of_area_axis_z=beam_dict.get('second_moment_of_area_axis_z', 0.0),
            radius_of_gyration_axis_y=beam_dict.get('radius_of_gyration_axis_y', 0.0),
            radius_of_gyration_axis_z=beam_dict.get('radius_of_gyration_axis_z', 0.0),
            elastic_modulus_axis_y=beam_dict.get('elastic_modulus_axis_y', 0.0),
            elastic_modulus_axis_z=beam_dict.get('elastic_modulus_axis_z', 0.0),
            plastic_modulus_axis_y=beam_dict.get('plastic_modulus_axis_y', 0.0),
            plastic_modulus_axis_z=beam_dict.get('plastic_modulus_axis_z', 0.0),
            buckling_parameter=beam_dict.get('buckling_parameter', 0.0),
            torsional_index=beam_dict.get('torsional_index', 0.0),
            warping_constant=beam_dict.get('warping_constant', 0.0),
            torsional_constant=beam_dict.get('torsional_constant', 0.0),
            area_of_section=beam_dict.get('area_of_section', 0.0),
        )


# Convenience functions for backward compatibility
def get_beams_grpc(server_address: str = "localhost:9090") -> List[Dict[str, Any]]:
    """Get all beams using gRPC"""
    with SteelBeamGRPCClient(server_address) as client:
        return client.get_all_beams()


def get_beam_grpc(section_designation: str, server_address: str = "localhost:9090") -> Optional[Dict[str, Any]]:
    """Get a specific beam using gRPC"""
    with SteelBeamGRPCClient(server_address) as client:
        return client.get_beam(section_designation)


def create_beam_grpc(beam_data: Dict[str, Any], server_address: str = "localhost:9090") -> Dict[str, Any]:
    """Create a new beam using gRPC"""
    with SteelBeamGRPCClient(server_address) as client:
        return client.create_beam(beam_data)


def get_stock_status_grpc(product_id: str, postcode: str, server_address: str = "localhost:9090") -> Dict[str, Any]:
    """Get stock status using gRPC"""
    with SteelBeamGRPCClient(server_address) as client:
        return client.get_stock_status(product_id, postcode)
