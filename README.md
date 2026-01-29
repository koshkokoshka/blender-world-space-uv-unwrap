# World Space UV Unwrap (Blender Add-on)

**World Space UV Unwrap** is a Blender add-on designed for **Hammer-style level editing workflows**.

It is intended for **brush-based / BSP-style level geometry**, making it easy to generate UVs with consistent world-space texture alignment across level environment.

## Installation

1. Download the [latest release](https://github.com/koshkokoshka/blender-world-space-uv-unwrap/releases)
2. In Blender, go to `Edit -> Preferences -> Add-ons -> Install...`
3. Select the downloaded `.zip` file and enable the add-on

## Usage

1. Enter **Edit Mode**
2. Select the mesh faces you want to unwrap
3. Use `UV -> Unwrap World Space`

![screenshot](https://github.com/user-attachments/assets/f87b9afa-399c-4ede-86b5-53bd02fd708f)

UVs will be generated immediately using world-space coordinates.
You can adjust **scale**, **offset**, and **rotation** in the operator panel (bottom-left).
