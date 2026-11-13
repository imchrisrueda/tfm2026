import argparse
import io
import json
import math
from pathlib import Path
import tempfile
import unittest
import unittest.mock

from PIL import Image, ImageCms
from prepare_fullframe_masters import exact_size, geometry_metadata, run_pipeline, digest


class FullframeTests(unittest.TestCase):
    def test_exact_ratio_no_upscale(self):
        for source, expected in [((3008, 2000),(1880,1250)),((3872,2592),(1936,1296)),
                                 ((6000,4000),(2046,1364)),((4032,3024),(2048,1536)),
                                 ((2592,3872),(1296,1936)),((640,480),(640,480))]:
            result = exact_size(*source,2048)
            self.assertEqual(result, expected)
            self.assertEqual(result[0]*source[1], result[1]*source[0])
        self.assertEqual(exact_size(3008,2000,0),(3008,2000))
        with self.assertRaises(ValueError): exact_size(1999,1000,100)
        with self.assertRaises(ValueError): exact_size(10,10,-1)

    def test_geometry_not_required_or_silently_approved(self):
        row = dict(sha256='hash',oriented_width=300,oriented_height=200,pot_diameter_exterior_cm=10)
        self.assertEqual(geometry_metadata(row,None,.5)['metric_reference_status'],'not_measured')
        annotation=dict(source_sha256='hash',review_status='accepted',reference_quality='usable',measurement_scope='pilot_only')
        self.assertEqual(geometry_metadata(row,annotation,.5)['metric_reference_status'],'annotation_not_approved_for_measurement')
        annotation.update(measurement_scope='reviewed',coordinate_space='exif_oriented',reviewer='tester',review_date='2026-11-12',pot_center_x_px=150,pot_center_y_px=100,pot_diameter_px=100)
        result = geometry_metadata(row,annotation,.5)
        self.assertEqual(result['output_px_per_cm'],5)
        self.assertEqual(result['fullframe_field_width_cm'],30)
        self.assertEqual(result['pot_diameter_output_px'],50)
        self.assertEqual(result['pot_center_output_x_px'],75)

    def fixture(self, root):
        path = root/'source.jpg'
        image = Image.new('RGB',(300,200),(20,90,30))
        image.putpixel((0,0),(255,0,0))
        exif = Image.Exif(); exif[274]=6
        profile = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
        image.save(path,exif=exif,icc_profile=profile)
        rows = []
        for index, (partition, role, active) in enumerate([('C_fit',None,True),('C_val','model_selection',True),('C_val','threshold_calibration',True),('G_fit',None,True),('T_real',None,True),('M_aux',None,True),('C_fit',None,False)]):
            rows.append(dict(image_id=f'image{index}',source_path='source.jpg',sha256=digest(path),oriented_width=200,oriented_height=300,year=2025,pot_diameter_exterior_cm=10,split_assignment=partition,validation_role=role,use_in_assigned_partition=active,split_group_id=f'group{index}',species_code='P',geometry_status='not_measured'))
        manifest=root/'manifest.json'; manifest.write_text(json.dumps(rows),encoding='utf-8')
        config=root/'config.json'; config.write_text(json.dumps(dict(status='pilot',strategy='full_frame_exact_aspect',max_long_edge=150,png_compress_level=3)),encoding='utf-8')
        return argparse.Namespace(manifest=manifest,config=config,output=root/'out',mode='pilot',selection=None,annotations=None,include_test=False,workers=2,resume=False), rows

    def test_pipeline_partition_color_orientation_and_resume(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            args, source=self.fixture(root)
            with unittest.mock.patch('builtins.print'):
                report=run_pipeline(args,root)
            self.assertEqual(report['counts']['fullframe_master_created'],1)
            self.assertEqual(report['counts']['held_out_T_real_not_opened'],1)
            rows=json.loads((args.output/'manifest_fullframe.json').read_text(encoding='utf-8'))
            self.assertEqual([r['split_assignment'] for r in rows],[r['split_assignment'] for r in source])
            self.assertEqual([r['split_group_id'] for r in rows],[r['split_group_id'] for r in source])
            self.assertFalse(rows[4]['master_image_path'])
            master=root/rows[0]['master_image_path']
            with Image.open(master) as image:
                self.assertEqual(image.size,(100,150)); self.assertEqual(image.mode,'RGB')
                self.assertTrue(image.info.get('icc_profile'))
                self.assertIsNone(image.getexif().get(274))
            self.assertEqual(rows[0]['scale_normalization_status'],'not_metric_normalized')
            self.assertEqual(rows[0]['geometry_status'],'not_measured')
            self.assertEqual(rows[0]['retained_source_area_fraction'],1)
            args.resume=True
            with unittest.mock.patch('builtins.print'):
                resumed=run_pipeline(args,root)
            self.assertEqual(resumed['counts'],report['counts'])
            master.write_bytes(b'changed')
            with self.assertRaises(ValueError): run_pipeline(args,root)

    def test_apply_frozen_gate_and_separate_roles(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); args,_=self.fixture(root)
            args.mode='apply'
            with self.assertRaises(ValueError): run_pipeline(args,root)
            config=json.loads(args.config.read_text());config.update(status='frozen',frozen_utc='2999-01-01T00:00:00+00:00');args.config.write_text(json.dumps(config))
            with self.assertRaises(ValueError): run_pipeline(args,root)
            config=json.loads(args.config.read_text());config['status']='frozen';config['frozen_utc']='2026-01-01T00:00:00+00:00';args.config.write_text(json.dumps(config))
            with unittest.mock.patch('builtins.print'):
                report=run_pipeline(args,root)
            self.assertEqual(report['counts']['fullframe_master_created'],5)
            self.assertEqual(set(report['active_master_counts_by_partition']),{'C_fit','C_val_model_selection','C_val_calibration','G_fit','M_aux'})
            args.output=root/'including_test';args.include_test=True
            with unittest.mock.patch('builtins.print'):
                report=run_pipeline(args,root)
            self.assertEqual(report['counts']['fullframe_master_created'],6)
            self.assertIn('T_real',report['active_master_counts_by_partition'])

    def test_changed_source_is_not_processed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);args,_=self.fixture(root)
            (root/'source.jpg').write_bytes(b'changed')
            with unittest.mock.patch('builtins.print'):
                report=run_pipeline(args,root)
            self.assertEqual(report['counts']['fullframe_processing_error'],1)
            self.assertEqual(report['errors'][0]['reason'],'source_hash_mismatch')
            self.assertEqual(report['active_master_counts_by_partition'],{})


if __name__=='__main__':
    unittest.main()
