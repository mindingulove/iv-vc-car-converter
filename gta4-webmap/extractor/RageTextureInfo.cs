/**********************************************************************\

 RageLib
 Copyright (C) 2008  Arushan/Aru <oneforaru at gmail.com>

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.

\**********************************************************************/

using System;
using System.IO;
using RageLib.Common;
using RageLib.Common.Resources;

namespace RageLib.Textures.Resource
{
    // rage::grcTexturePC
    public class TextureInfo : IFileAccess
    {
        public File File { get; set; }

        public uint VTable { get; private set; }

        private uint BlockMapOffset { get; set; } // 0 in file

        private uint Unknown1 { get; set; } // 1 / 0x10000 on PC (really composed of a BYTE, BYTE, WORD)
        private uint Unknown2 { get; set; } // 0
        private uint Unknown3 { get; set; } // 0

        public string Name { get; private set; }
        private uint Unknown4 { get; set; } // 0;   // set in memory by game

        public ushort Width { get; private set; }
        public ushort Height { get; private set; }

        public D3DFormat Format;

        private ushort StrideSize { get; set; }
        private byte Type { get; set; }   // 0 = normal, 1 = cube, 3 = volume
        public byte Levels { get; set; } // MipMap levels

        private float UnknownFloat1 { get; set; } // 1.0f
        private float UnknownFloat2 { get; set; } // 1.0f
        private float UnknownFloat3 { get; set; } // 1.0f
        private float UnknownFloat4 { get; set; } // 0
        private float UnknownFloat5 { get; set; } // 0
        private float UnknownFloat6 { get; set; } // 0

        private uint PrevTextureInfoOffset { get; set; }    // sometimes not always accurate
        private uint NextTextureInfoOffset { get; set; }    // always 0

        internal uint RawDataOffset { get; set; }
        public byte[] TextureData { get; private set; }
        internal int TextureDataOffset { get; private set; }
        internal int TextureDataLength { get; private set; }

        private uint Unknown6 { get; set; }

        public void ReadData(byte[] graphicsMemData)
        {
            int dataSize = GetTotalDataSize();
            TextureData = graphicsMemData;
            TextureDataOffset = (int)RawDataOffset;
            TextureDataLength = dataSize;
        }

        public void ReadData(BinaryReader br)
        {
            int dataSize = GetTotalDataSize();
            br.BaseStream.Seek(RawDataOffset, SeekOrigin.Begin);
            TextureData = br.ReadBytes(dataSize);
            TextureDataOffset = 0;
            TextureDataLength = dataSize;
        }

        internal int GetTotalDataSize()
        {
            // Count every mip in complete 4x4 DXT blocks, including 2x2/1x1.
            // Dividing the preceding byte count by four truncates those levels
            // and is also wrong for non-square and non-block-aligned textures.
            uint width = Width, height = Height;
            int dataSize = 0;
            for (int level = 0; level < Math.Max(1, (int)Levels); level++)
            {
                uint size;
                switch (Format)
                {
                    case D3DFormat.DXT1:
                        size = checked(Math.Max(1u, (width + 3) / 4) * Math.Max(1u, (height + 3) / 4) * 8);
                        break;
                    case D3DFormat.DXT3:
                    case D3DFormat.DXT5:
                        size = checked(Math.Max(1u, (width + 3) / 4) * Math.Max(1u, (height + 3) / 4) * 16);
                        break;
                    case D3DFormat.A8R8G8B8: size = checked(width * height * 4); break;
                    case D3DFormat.L8:
                    case (D3DFormat)0x1c: size = checked(width * height); break; // D3DFMT_A8
                    default: throw new InvalidDataException($"Unsupported texture {Name} pixel format 0x{(uint)Format:X}");
                }
                dataSize = checked(dataSize + (int)size);
                width = Math.Max(1u, width / 2); height = Math.Max(1u, height / 2);
            }
            return dataSize;
        }

        public void WriteData(BinaryWriter bw)
        {
            bw.BaseStream.Seek(RawDataOffset, SeekOrigin.Begin);
            bw.Write(TextureData);
        }

        #region IFileAccess Members

        public void Read(BinaryReader br)
        {
            // Full structure of rage::grcTexturePC

            // rage::datBase
            VTable = br.ReadUInt32();

            // rage::pgBase
            BlockMapOffset = ResourceUtil.ReadOffset(br);

            // Texture Info struct:
            Unknown1 = br.ReadUInt32(); // BYTE, BYTE, WORD
            Unknown2 = br.ReadUInt32();
            Unknown3 = br.ReadUInt32();

            uint nameOffset = ResourceUtil.ReadOffset(br);

            Unknown4 = br.ReadUInt32();

            // Texture Data struct:
            Width = br.ReadUInt16();
            Height = br.ReadUInt16();
            Format = (D3DFormat) br.ReadInt32();

            StrideSize = br.ReadUInt16();
            Type = br.ReadByte();
            Levels = br.ReadByte();

            UnknownFloat1 = br.ReadSingle();
            UnknownFloat2 = br.ReadSingle();
            UnknownFloat3 = br.ReadSingle();
            UnknownFloat4 = br.ReadSingle();
            UnknownFloat5 = br.ReadSingle();
            UnknownFloat6 = br.ReadSingle();

            PrevTextureInfoOffset = ResourceUtil.ReadOffset(br);
            NextTextureInfoOffset = ResourceUtil.ReadOffset(br);

            RawDataOffset = ResourceUtil.ReadDataOffset(br);

            Unknown6 = br.ReadUInt32();

            // Read texture name
            br.BaseStream.Seek(nameOffset, SeekOrigin.Begin);
            Name = ResourceUtil.ReadNullTerminatedString(br);
        }

        public void Write(BinaryWriter bw)
        {
            throw new NotImplementedException();
        }

        #endregion
    }
}
