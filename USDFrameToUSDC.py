from pxr import Usd, UsdGeom, Sdf, Vt
import os
import sys
import gc
import argparse
from pathlib import Path

def print_usd_tree(usd_file: str, max_depth: int = None):
    """
    Affiche la hiérarchie des prims d'un fichier USD (comme usdtree)
    """
    if not os.path.exists(usd_file):
        print(f"[ERROR] File not found: {usd_file}", file=sys.stderr)
        sys.exit(1)
    
    print(f"\n=== USD Tree: {usd_file} ===\n")
    
    try:
        stage = Usd.Stage.Open(usd_file)
        
        # Infos générales
        print(f"Layer: {stage.GetRootLayer().identifier}")
        print(f"Time Range: {stage.GetStartTimeCode()} - {stage.GetEndTimeCode()}")
        print(f"Frame Rate: {stage.GetFramesPerSecond()}")
        print(f"\nPrim Hierarchy:\n")
        
        def print_prim(prim, indent=0, current_depth=0):
            """Affiche récursivement les prims"""
            if max_depth is not None and current_depth > max_depth:
                return
            
            # Symbole selon le type
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
            
            # Nom et type
            prim_type = prim.GetTypeName()
            prefix = "  " * indent
            print(f"{prefix}{symbol} {prim.GetName()} ({prim_type})")
            
            # Afficher les attributs principaux si c'est un Points ou Mesh
            if indent < 3 and (prim.IsA(UsdGeom.Points) or prim.IsA(UsdGeom.Mesh)):
                attrs = prim.GetAttributes()
                interesting_attrs = []
                
                for attr in attrs:
                    attr_name = attr.GetName()
                    # Filtrer les attributs intéressants
                    if any(key in attr_name for key in ['primvar', 'points', 'velocities', 'normals', 'ids']):
                        value = attr.Get()
                        if value is not None and hasattr(value, '__len__'):
                            interesting_attrs.append(f"{attr_name} [{len(value)}]")
                        else:
                            interesting_attrs.append(attr_name)
                
                if interesting_attrs:
                    attrs_str = ", ".join(interesting_attrs[:5])  # Limiter à 5
                    if len(interesting_attrs) > 5:
                        attrs_str += f" ... (+{len(interesting_attrs) - 5} more)"
                    print(f"{prefix}  └─ Attributes: {attrs_str}")
            
            # Récursion sur les enfants
            for child in prim.GetChildren():
                print_prim(child, indent + 1, current_depth + 1)
        
        # Commencer par le root
        root = stage.GetPseudoRoot()
        for child in root.GetChildren():
            print_prim(child)
        
        print("\n" + "="*50 + "\n")
        
    except Exception as e:
        print(f"[ERROR] Failed to read USD file: {e}", file=sys.stderr)
        sys.exit(1)


def merge_usd_sequence_to_single_file(
    input_pattern: str,
    output_file: str,
    frame_range: tuple,
    prim_path: str = "/Root/Points",
    save_interval: int = 10
):
    """
    Fusionne une séquence d'USD (1 par frame) en un seul fichier avec time samples.
    Version optimisée mémoire.
    """
    
    start_frame, end_frame = frame_range
    
    # Créer le stage de sortie
    output_stage = Usd.Stage.CreateNew(output_file)
    output_stage.SetStartTimeCode(start_frame)
    output_stage.SetEndTimeCode(end_frame)
    
    print(f"Création du fichier: {output_file}")
    print(f"Frame range: {start_frame}-{end_frame}")
    print(f"Save interval: every {save_interval} frames")
    
    # Pour chaque frame
    for frame in range(start_frame, end_frame + 1):
        time_code = Usd.TimeCode(frame)
        
        # Ouvrir le fichier source de cette frame
        input_file = input_pattern.format(frame=frame)
        
        if not os.path.exists(input_file):
            print(f"[WARNING] Frame {frame} manquante: {input_file}")
            continue
            
        print(f"Processing frame {frame}... ", end="", flush=True)
        
        # Ouvrir le stage source
        source_stage = Usd.Stage.Open(input_file)
        source_prim = source_stage.GetPrimAtPath(prim_path)
        
        if not source_prim.IsValid():
            print(f"[ERROR] Prim '{prim_path}' non trouvé")
            # Fermer le stage et libérer mémoire
            del source_stage
            gc.collect()
            continue
        
        # Si c'est la première frame, créer la structure
        if frame == start_frame:
            # Créer le prim Points dans le stage de sortie
            output_prim = output_stage.DefinePrim(prim_path, "Points")
            points_api = UsdGeom.Points(output_prim)
            
            # Copier tous les attributs (structure)
            for attr in source_prim.GetAttributes():
                attr_name = attr.GetName()
                type_name = attr.GetTypeName()
                
                # Créer l'attribut dans le output
                output_attr = output_prim.CreateAttribute(attr_name, type_name)
                
                # IMPORTANT : Désactiver l'interpolation pour les types non-interpolables
                if type_name.type.pythonClass in [int, str] or 'int' in str(type_name).lower():
                    output_attr.SetMetadata('interpolation', 'held')
                    print(f"\n  - Attribut créé (NO INTERP): {attr_name} ({type_name})")
                else:
                    print(f"\n  - Attribut créé: {attr_name} ({type_name})")
        
        # Maintenant, copier les VALEURS de cette frame
        output_prim = output_stage.GetPrimAtPath(prim_path)
        
        for attr in source_prim.GetAttributes():
            attr_name = attr.GetName()
            value = attr.Get()
            
            # IMPORTANT : Skip les attributs sans valeur (None/void)
            if value is None:
                continue
            
            # Écrire la valeur à ce time code
            output_attr = output_prim.GetAttribute(attr_name)
            output_attr.Set(value, time_code)
        
        print("OK")
        
        # CRITIQUE : Fermer le stage source et forcer le garbage collection
        del source_stage
        del source_prim
        gc.collect()
        
        # Flush périodique du stage de sortie
        if frame % save_interval == 0:
            output_stage.GetRootLayer().Save()
            print(f" [SAVED at frame {frame}]")
    
    # Sauvegarde finale
    output_stage.GetRootLayer().Save()
    print(f"\n[SUCCESS] File created: {output_file}")
    print(f"   Size: {os.path.getsize(output_file) / (1024**3):.2f} GB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='USD Tools: Merge frame sequences or inspect USD files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Merge Examples:
  # Basic usage with default prim path (/Root/Points)
  python USDFrameToUSDC.py -i "./sim/frame_{frame:04d}.usd" -o merged.usdc -s 0 -e 200
  
  # With custom prim path
  python USDFrameToUSDC.py -i "./FlipSystem.fluid.{frame:04d}.usd" -o output.usdc -s 1 -e 250 -p /Root/Points
  
  # With custom save interval (save every 5 frames to save RAM)
  python USDFrameToUSDC.py -i "./sim/frame_{frame:04d}.usd" -o merged.usdc -s 0 -e 500 --save-interval 5
  
  # Full example with all options
  python USDFrameToUSDC.py -i "./sim/frame_{frame:04d}.usd" -o output.usdc -s 1 -e 100 -p /World/Particles --save-interval 20

Tree Inspection Examples:
  # Display USD hierarchy
  python USDFrameToUSDC.py -t frame_0001.usd
  
  # Display with depth limit
  python USDFrameToUSDC.py -t frame_0001.usd --max-depth 3

Note:
  The input pattern must contain {frame:04d} or similar formatting for frame numbers.
  Example: "frame_{frame:04d}.usd" will look for frame_0001.usd, frame_0002.usd, etc.
        """
    )
    
    # Mode selection: merge or tree
    parser.add_argument('-t', '--tree', metavar='USD_FILE',
                        help='Display USD file hierarchy (like usdtree)')
    parser.add_argument('--max-depth', type=int, default=None,
                        help='Maximum depth for tree display (default: unlimited)')
    
    # Merge arguments
    parser.add_argument('-i', '--input',
                        help='Input USD file pattern (e.g., "./sim/frame_{frame:04d}.usd")')
    parser.add_argument('-o', '--output',
                        help='Output USD file path (e.g., "merged.usdc")')
    parser.add_argument('-s', '--start', type=int,
                        help='Start frame number')
    parser.add_argument('-e', '--end', type=int,
                        help='End frame number')
    parser.add_argument('-p', '--prim-path', default='/Root/Points',
                        help='Prim path in USD file (default: /Root/Points)')
    parser.add_argument('--save-interval', type=int, default=10,
                        help='Save file every N frames to free memory (default: 10)')
    
    args = parser.parse_args()
    
    # Mode tree
    if args.tree:
        print_usd_tree(args.tree, args.max_depth)
        sys.exit(0)
    
    # Mode merge - validation
    if not all([args.input, args.output, args.start is not None, args.end is not None]):
        parser.error("Merge mode requires: -i, -o, -s, -e arguments")
    
    if args.start > args.end:
        parser.error(f"Start frame ({args.start}) cannot be greater than end frame ({args.end})")
    
    if args.save_interval < 1:
        parser.error(f"Save interval must be at least 1 (got {args.save_interval})")
    
    if '{frame' not in args.input:
        parser.error(f"Input pattern must contain frame placeholder (e.g., '{{frame:04d}}')")
    
    # Execute merge
    try:
        merge_usd_sequence_to_single_file(
            input_pattern=args.input,
            output_file=args.output,
            frame_range=(args.start, args.end),
            prim_path=args.prim_path,
            save_interval=args.save_interval
        )
    except Exception as e:
        print(f"\n[ERROR] An error occurred: {e}", file=sys.stderr)
        sys.exit(1)