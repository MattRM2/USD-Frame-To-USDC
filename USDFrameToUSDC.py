#!/usr/bin/python
from pxr import Usd, UsdGeom, Sdf
import sys
import os
import gc
import argparse
import time

def print_usd_tree(usd_file: str, max_depth: int = None):
    """
    Display USD file hierarchy (like usdtree)
    """
    if not os.path.exists(usd_file):
        print(f"[ERROR] File not found: {usd_file}", file=sys.stderr)
        sys.exit(1)
    
    print(f"\n=== USD Tree: {usd_file} ===\n")
    
    try:
        stage = Usd.Stage.Open(usd_file)
        
        # General info
        print(f"Layer: {stage.GetRootLayer().identifier}")
        print(f"Time Range: {stage.GetStartTimeCode()} - {stage.GetEndTimeCode()}")
        print(f"Frame Rate: {stage.GetFramesPerSecond()}")
        print(f"\nPrim Hierarchy:\n")
        
        def print_prim(prim, indent=0, current_depth=0):
            """Recursively display prims"""
            if max_depth is not None and current_depth > max_depth:
                return
            
            # Symbol by type
            if prim.IsA(UsdGeom.Xform):
                symbol = "📦"
            elif prim.IsA(UsdGeom.Mesh):
                symbol = "🔷"
            elif prim.IsA(UsdGeom.Points):
                symbol = "⚫"
            elif prim.IsA(UsdGeom.Camera):
                symbol = "📷"
            else:
                symbol = "📄"
            
            # Name and type
            prim_type = prim.GetTypeName()
            prefix = "  " * indent
            print(f"{prefix}{symbol} {prim.GetName()} ({prim_type})")
            
            # Display all attributes for Points or Mesh
            if indent < 3 and (prim.IsA(UsdGeom.Points) or prim.IsA(UsdGeom.Mesh)):
                attrs = prim.GetAttributes()
                all_attrs = []
                
                for attr in attrs:
                    attr_name = attr.GetName()
                    if any(key in attr_name for key in ['primvar', 'points', 'velocities', 'normals', 'ids']):
                        value = attr.Get()
                        if value is not None and hasattr(value, '__len__'):
                            all_attrs.append(f"{attr_name} [{len(value)}]")
                        else:
                            all_attrs.append(attr_name)
                
                if all_attrs:
                    attrs_str = ", ".join(all_attrs)
                    print(f"{prefix}  └─ Attributes: {attrs_str}")
            
            # Recursion on children
            for child in prim.GetChildren():
                print_prim(child, indent + 1, current_depth + 1)
        
        # Start from root
        root = stage.GetPseudoRoot()
        for child in root.GetChildren():
            print_prim(child)
        
        print("\n" + "="*50 + "\n")
        
    except Exception as e:
        print(f"[ERROR] Failed to read USD file: {e}", file=sys.stderr)
        sys.exit(1)


def merge_prim_recursive(
    source_prim: Usd.Prim,
    output_prim: Usd.Prim,
    frame: float,
    is_first_frame: bool
):
    """
    Recursively merge a prim and all its children with time samples
    """
    # Copy prim type if first frame
    if is_first_frame:
        if source_prim.GetTypeName():
            output_prim.SetTypeName(source_prim.GetTypeName())
    
    # Copy all attributes
    for attr in source_prim.GetAttributes():
        attr_name = attr.GetName()
        output_attr = output_prim.GetAttribute(attr_name)
        
        if is_first_frame and not output_attr:
            # Create attribute on first frame
            output_attr = output_prim.CreateAttribute(
                attr_name,
                attr.GetTypeName(),
                custom=attr.IsCustom()
            )
            
            # Copy metadata
            for key in attr.GetAllMetadata():
                if key not in ['default', 'timeSamples']:
                    output_attr.SetMetadata(key, attr.GetMetadata(key))
            
            # Disable interpolation for integer types
            type_name = attr.GetTypeName()
            if type_name.type.pythonClass in [int, str] or 'int' in str(type_name).lower():
                output_attr.SetMetadata('interpolation', 'held')
        
        # Set time sample
        value = attr.Get()
        if value is not None:
            output_attr.Set(value, frame)
    
    # Recursively process children
    for child in source_prim.GetChildren():
        child_name = child.GetName()
        output_child = output_prim.GetChild(child_name)
        
        if is_first_frame and not output_child:
            # Create child prim if doesn't exist
            output_child = output_prim.GetStage().DefinePrim(
                output_prim.GetPath().AppendChild(child_name)
            )
        
        if output_child:
            merge_prim_recursive(child, output_child, frame, is_first_frame)


def merge_single_prim(
    input_pattern: str,
    output_file: str,
    frame_range: tuple,
    prim_path: str,
    save_interval: int
):
    """
    Merge a single prim from USD sequence (original behavior)
    """
    start_frame, end_frame = frame_range
    
    print(f"\n=== Merging Single Prim: {prim_path} ===")
    print(f"Input: {input_pattern}")
    print(f"Output: {output_file}")
    print(f"Frame range: {start_frame} - {end_frame}")
    print(f"Save interval: {save_interval}\n")
    
    # Create output stage
    output_stage = Usd.Stage.CreateNew(output_file)
    output_stage.SetStartTimeCode(start_frame)
    output_stage.SetEndTimeCode(end_frame)
    
    frames_processed = 0
    
    for frame in range(start_frame, end_frame + 1):
        input_file = input_pattern.format(frame=frame)
        
        if not os.path.exists(input_file):
            print(f"[WARNING] Frame {frame} not found: {input_file}")
            continue
        
        try:
            # Open source stage
            source_stage = Usd.Stage.Open(input_file)
            source_prim = source_stage.GetPrimAtPath(prim_path)
            
            if not source_prim or not source_prim.IsValid():
                print(f"[WARNING] Prim '{prim_path}' not found in frame {frame}")
                del source_stage
                gc.collect()
                continue
            
            # Get or create output prim
            output_prim = output_stage.GetPrimAtPath(prim_path)
            if not output_prim:
                output_prim = output_stage.DefinePrim(prim_path)
            
            is_first_frame = (frames_processed == 0)
            
            # Copy prim type if first frame
            if is_first_frame:
                output_prim.SetTypeName(source_prim.GetTypeName())
            
            # Copy all attributes with time samples
            for attr in source_prim.GetAttributes():
                attr_name = attr.GetName()
                output_attr = output_prim.GetAttribute(attr_name)
                
                if is_first_frame and not output_attr:
                    # Create attribute on first frame
                    output_attr = output_prim.CreateAttribute(
                        attr_name,
                        attr.GetTypeName(),
                        custom=attr.IsCustom()
                    )
                    
                    # Copy metadata
                    for key in attr.GetAllMetadata():
                        if key not in ['default', 'timeSamples']:
                            output_attr.SetMetadata(key, attr.GetMetadata(key))
                    
                    # Disable interpolation for integer types
                    type_name = attr.GetTypeName()
                    if type_name.type.pythonClass in [int, str] or 'int' in str(type_name).lower():
                        output_attr.SetMetadata('interpolation', 'held')
                
                # Set time sample
                value = attr.Get()
                if value is not None:
                    output_attr.Set(value, frame)
            
            frames_processed += 1
            print(f"Frame {frame}: ✓ Merged ({frames_processed} total)")
            
            # Periodic save
            if frames_processed % save_interval == 0:
                output_stage.Save()
                print(f"  → Saved checkpoint ({frames_processed} frames)")
            
            # Clean up
            del source_stage, source_prim
            gc.collect()
            
        except Exception as e:
            print(f"[ERROR] Frame {frame}: {e}")
            continue
    
    # Final save
    output_stage.Save()
    print(f"\n✓ Merge complete: {frames_processed} frames merged to {output_file}")


def merge_full_usd(
    input_pattern: str,
    output_file: str,
    frame_range: tuple,
    save_interval: int
):
    """
    Merge entire USD (all prims) from sequence (new default behavior)
    """
    start_frame, end_frame = frame_range
    
    print(f"\n=== Merging Full USD (All Prims) ===")
    print(f"Input: {input_pattern}")
    print(f"Output: {output_file}")
    print(f"Frame range: {start_frame} - {end_frame}")
    print(f"Save interval: {save_interval}\n")
    
    # Create output stage
    output_stage = Usd.Stage.CreateNew(output_file)
    output_stage.SetStartTimeCode(start_frame)
    output_stage.SetEndTimeCode(end_frame)
    
    frames_processed = 0
    
    for frame in range(start_frame, end_frame + 1):
        input_file = input_pattern.format(frame=frame)
        
        if not os.path.exists(input_file):
            print(f"[WARNING] Frame {frame} not found: {input_file}")
            continue
        
        try:
            # Open source stage
            source_stage = Usd.Stage.Open(input_file)
            
            is_first_frame = (frames_processed == 0)
            
            # Copy stage metadata on first frame
            if is_first_frame:
                output_stage.SetMetadata('upAxis', source_stage.GetMetadata('upAxis'))
                output_stage.SetMetadata('metersPerUnit', source_stage.GetMetadata('metersPerUnit'))
                if source_stage.HasAuthoredTimeCodesPerSecond():
                    output_stage.SetTimeCodesPerSecond(source_stage.GetTimeCodesPerSecond())
                if source_stage.HasAuthoredFramesPerSecond():
                    output_stage.SetFramesPerSecond(source_stage.GetFramesPerSecond())
            
            # Process all root prims recursively
            for source_prim in source_stage.GetPseudoRoot().GetChildren():
                prim_path = source_prim.GetPath()
                output_prim = output_stage.GetPrimAtPath(prim_path)
                
                if is_first_frame and not output_prim:
                    output_prim = output_stage.DefinePrim(prim_path)
                
                if output_prim:
                    merge_prim_recursive(source_prim, output_prim, frame, is_first_frame)
            
            frames_processed += 1
            print(f"Frame {frame}: ✓ Merged ({frames_processed} total)")
            
            # Periodic save
            if frames_processed % save_interval == 0:
                output_stage.Save()
                print(f"  → Saved checkpoint ({frames_processed} frames)")
            
            # Clean up
            del source_stage
            gc.collect()
            
        except Exception as e:
            print(f"[ERROR] Frame {frame}: {e}")
            continue
    
    # Final save
    output_stage.Save()
    print(f"\n✓ Merge complete: {frames_processed} frames merged to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='USD Frame Merger: Merge USD frame sequences into single time-sampled USD file.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Merge entire USD (all prims) - DEFAULT BEHAVIOR
  python USDFrameToUSDC.py -i "./sim/frame_{frame:04d}.usd" -o merged.usdc -s 0 -e 200
  
  # Merge only specific prim (original behavior)
  python USDFrameToUSDC.py -i "./sim/frame_{frame:04d}.usd" -o merged.usdc -s 0 -e 200 -p /Root/Points
  
  # With custom save interval for memory management
  python USDFrameToUSDC.py -i "./sim/frame_{frame:04d}.usd" -o merged.usdc -s 0 -e 500 --save-interval 20
  
  # Tree inspection
  python USDFrameToUSDC.py -t frame_0001.usd
  python USDFrameToUSDC.py -t frame_0001.usd --max-depth 3

Note:
  - By default, merges ALL prims in the USD hierarchy
  - Use -p to merge only a specific prim (faster, less memory)
  - Input pattern must contain {frame:04d} or similar placeholder
  - Save interval affects memory usage (lower = more saves, less memory)
        """
    )
    
    # Mode selection
    parser.add_argument('-t', '--tree', metavar='USD_FILE',
                        help='Display USD file hierarchy (like usdtree)')
    parser.add_argument('--max-depth', type=int, default=None,
                        help='Maximum depth for tree display')
    
    # Merge arguments
    parser.add_argument('-i', '--input',
                        help='Input USD file pattern (e.g., "./sim/frame_{frame:04d}.usd")')
    parser.add_argument('-o', '--output',
                        help='Output USD file (e.g., "merged.usdc")')
    parser.add_argument('-s', '--start', type=int,
                        help='Start frame number')
    parser.add_argument('-e', '--end', type=int,
                        help='End frame number')
    parser.add_argument('-p', '--prim-path',
                        help='Prim path to merge (optional - merges only this prim instead of entire USD)')
    parser.add_argument('--save-interval', type=int, default=10,
                        help='Save every N frames to manage memory (default: 10)')
    
    args = parser.parse_args()
    
    # Tree mode
    if args.tree:
        print_usd_tree(args.tree, args.max_depth)
        sys.exit(0)
    
    # Merge mode - validation
    if not all([args.input, args.output, args.start is not None, args.end is not None]):
        parser.error("Merge mode requires: -i, -o, -s, -e arguments")
    
    if args.start > args.end:
        parser.error(f"Start frame ({args.start}) cannot be greater than end frame ({args.end})")
    
    if '{frame' not in args.input:
        parser.error("Input pattern must contain frame placeholder (e.g., '{frame:04d}')")
    
    # Execute merge
    start_time = time.time()
    
    try:
        if args.prim_path:
            # Single prim mode (original behavior)
            merge_single_prim(
                args.input,
                args.output,
                (args.start, args.end),
                args.prim_path,
                args.save_interval
            )
        else:
            # Full USD mode (new default)
            merge_full_usd(
                args.input,
                args.output,
                (args.start, args.end),
                args.save_interval
            )
        
        # Time summary
        elapsed = time.time() - start_time
        minutes = int(elapsed // 60)
        seconds = elapsed % 60
        
        if minutes > 0:
            print(f"\nTotal time: {minutes}m {seconds:.1f}s")
        else:
            print(f"\nTotal time: {seconds:.1f}s")
        
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Merge cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] An error occurred: {e}", file=sys.stderr)
        sys.exit(1)